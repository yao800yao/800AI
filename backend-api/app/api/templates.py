import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.database import get_db
from app.models.template import Template
from app.models.template_tag import TemplateTag
from app.models.template_tag_relation import TemplateTagRelation
from app.models.user import User
from app.schemas.template import (
    TemplateCreate,
    TemplateDetailOut,
    TemplateListItemOut,
    TemplateListResponse,
    TemplateTagPayload,
    TemplateTagOut,
    TemplateUpdate,
)
from app.services.image_delivery_service import get_optional_cos_config, serialize_asset_urls

router = APIRouter(prefix="/api/templates", tags=["创意模版"])


def _normalize_tag_name(name: str) -> str:
    return (name or "").strip()[:50]


def _normalize_tag_names(tag_names: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for name in tag_names:
        normalized = _normalize_tag_name(name)
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(normalized)
    return result


def _tag_sort_key(tag: TemplateTag) -> tuple:
    return (
        tag.parent_id is not None,
        tag.sort_order or 0,
        tag.name.lower(),
    )


def _count_tag_templates(tag: TemplateTag) -> int:
    return len(tag.template_relations)


def _count_parent_tag_templates(tag: TemplateTag) -> int:
    template_ids = {rel.template_id for rel in tag.template_relations}
    for child in tag.children or []:
        template_ids.update(rel.template_id for rel in child.template_relations)
    return len(template_ids)


def _serialize_tag(tag: TemplateTag) -> dict:
    is_parent = tag.parent_id is None
    template_count = _count_parent_tag_templates(tag) if is_parent else _count_tag_templates(tag)
    return {
        "id": tag.id,
        "name": tag.name,
        "parent_id": tag.parent_id,
        "sort_order": tag.sort_order or 0,
        "template_count": template_count,
    }


def _serialize_template_list_item(template: Template, *, cos_config=None) -> dict:
    result_asset = serialize_asset_urls(template.result_image or "", cos_config=cos_config)
    return {
        "id": template.id,
        "prompt": template.prompt or "",
        "model": template.model or "",
        "result_image": result_asset["image_url"],
        "result_image_thumb": result_asset["thumb_url"],
        "sort_order": template.sort_order or 0,
        "size": template.size,
        "resolution": template.resolution or "",
        "custom_size": template.custom_size or "",
        "num_images": 1,
        "tags": [
            {
                "id": rel.tag.id,
                "name": rel.tag.name,
                "parent_id": rel.tag.parent_id,
                "sort_order": rel.tag.sort_order or 0,
            }
            for rel in sorted(template.tag_relations, key=lambda rel: rel.tag.name.lower())
            if rel.tag
        ],
        "created_at": template.created_at,
    }


def _serialize_template_detail(template: Template, *, cos_config=None) -> dict:
    reference_assets = [
        serialize_asset_urls(url, cos_config=cos_config)
        for url in json.loads(template.reference_images or "[]")
    ]
    return {
        **_serialize_template_list_item(template, cos_config=cos_config),
        "reference_images": [asset["image_url"] for asset in reference_assets],
        "reference_image_thumbs": [asset["thumb_url"] for asset in reference_assets],
    }


def _find_duplicate_tag_name(db: Session, name: str, parent_id: int | None, exclude_id: int | None = None) -> TemplateTag | None:
    query = db.query(TemplateTag).filter(TemplateTag.name == name)
    if parent_id is None:
        query = query.filter(TemplateTag.parent_id.is_(None))
    else:
        query = query.filter(TemplateTag.parent_id == parent_id)
    if exclude_id is not None:
        query = query.filter(TemplateTag.id != exclude_id)
    return query.first()


def _validate_tag_parent(db: Session, parent_id: int | None, *, tag_id: int | None = None) -> TemplateTag | None:
    if parent_id is None:
        return None

    parent = db.query(TemplateTag).filter(TemplateTag.id == parent_id).first()
    if not parent:
        raise HTTPException(status_code=400, detail="所属大标签不存在")
    if parent.parent_id is not None:
        raise HTTPException(status_code=400, detail="只支持两级标签，小标签不能再有子标签")
    if tag_id is not None and parent_id == tag_id:
        raise HTTPException(status_code=400, detail="标签不能设置为自己所属的大标签")
    return parent


def _validate_assignable_tag(db: Session, tag: TemplateTag) -> None:
    if tag.parent_id is None:
        has_children = (
            db.query(TemplateTag.id)
            .filter(TemplateTag.parent_id == tag.id)
            .first()
        )
        if has_children:
            raise HTTPException(status_code=400, detail=f"标签「{tag.name}」是大标签，请使用其下的小标签")


def _sync_template_tags(db: Session, template: Template, tag_names: list[str]):
    normalized_names = _normalize_tag_names(tag_names)
    template.tag_relations.clear()
    db.flush()

    for tag_name in normalized_names:
        tag = db.query(TemplateTag).filter(TemplateTag.name == tag_name).first()
        if not tag:
            raise HTTPException(status_code=400, detail=f"标签「{tag_name}」不存在，请先在标签管理中创建")
        _validate_assignable_tag(db, tag)
        template.tag_relations.append(TemplateTagRelation(tag_id=tag.id))


def _child_tag_ids(db: Session, parent_id: int) -> list[int]:
    return [
        tag_id
        for (tag_id,) in db.query(TemplateTag.id).filter(TemplateTag.parent_id == parent_id).all()
    ]


def _apply_template_tag_filter(query, db: Session, *, tag_id: int | None, parent_id: int | None):
    if tag_id is not None:
        return query.join(TemplateTagRelation).filter(TemplateTagRelation.tag_id == tag_id)
    if parent_id is not None:
        child_ids = _child_tag_ids(db, parent_id)
        tag_ids = child_ids if child_ids else [parent_id]
        return query.join(TemplateTagRelation).filter(TemplateTagRelation.tag_id.in_(tag_ids))
    return query


@router.get("", response_model=TemplateListResponse)
def list_templates(
    tag_id: int | None = Query(None),
    parent_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if tag_id is not None and parent_id is not None:
        raise HTTPException(status_code=400, detail="tag_id 与 parent_id 不能同时传")

    cos_config = get_optional_cos_config(db)
    query = db.query(Template).order_by(Template.sort_order.desc(), Template.created_at.desc())
    query = _apply_template_tag_filter(query, db, tag_id=tag_id, parent_id=parent_id)
    total = query.count()
    templates = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "items": [_serialize_template_list_item(template, cos_config=cos_config) for template in templates],
    }


@router.get("/tags", response_model=list[TemplateTagOut])
def list_template_tags(db: Session = Depends(get_db)):
    tags = db.query(TemplateTag).all()
    tags.sort(key=_tag_sort_key)
    return [_serialize_tag(tag) for tag in tags]


@router.post("/tags", response_model=TemplateTagOut)
def create_template_tag(
    body: TemplateTagPayload,
    _user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    tag_name = _normalize_tag_name(body.name)
    if not tag_name:
        raise HTTPException(status_code=400, detail="标签名称不能为空")

    _validate_tag_parent(db, body.parent_id)
    if _find_duplicate_tag_name(db, tag_name, body.parent_id):
        raise HTTPException(status_code=400, detail="同级标签名称已存在")

    tag = TemplateTag(
        name=tag_name,
        parent_id=body.parent_id,
        sort_order=body.sort_order or 0,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return _serialize_tag(tag)


@router.put("/tags/{tag_id}", response_model=TemplateTagOut)
def update_template_tag(
    tag_id: int,
    body: TemplateTagPayload,
    _user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    tag = db.query(TemplateTag).filter(TemplateTag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")

    tag_name = _normalize_tag_name(body.name)
    if not tag_name:
        raise HTTPException(status_code=400, detail="标签名称不能为空")

    has_children = (
        db.query(TemplateTag.id)
        .filter(TemplateTag.parent_id == tag.id)
        .first()
    )
    if has_children and body.parent_id is not None:
        raise HTTPException(status_code=400, detail="大标签不能设置所属大标签")

    next_parent_id = None if has_children else body.parent_id

    _validate_tag_parent(db, next_parent_id, tag_id=tag.id)
    if _find_duplicate_tag_name(db, tag_name, next_parent_id, exclude_id=tag.id):
        raise HTTPException(status_code=400, detail="同级标签名称已存在")

    tag.name = tag_name
    tag.parent_id = next_parent_id
    tag.sort_order = body.sort_order if body.sort_order is not None else (tag.sort_order or 0)
    db.commit()
    db.refresh(tag)
    return _serialize_tag(tag)


@router.delete("/tags/{tag_id}")
def delete_template_tag(
    tag_id: int,
    _user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    tag = db.query(TemplateTag).filter(TemplateTag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")

    db.delete(tag)
    db.commit()
    return {"message": "删除成功"}


@router.get("/admin/list", response_model=list[TemplateListItemOut])
def list_admin_templates(
    _user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    cos_config = get_optional_cos_config(db)
    templates = db.query(Template).order_by(Template.sort_order.desc(), Template.created_at.desc()).all()
    return [_serialize_template_list_item(template, cos_config=cos_config) for template in templates]


@router.get("/{template_id}", response_model=TemplateDetailOut)
def get_template_detail(template_id: int, db: Session = Depends(get_db)):
    cos_config = get_optional_cos_config(db)
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模版不存在")
    return _serialize_template_detail(template, cos_config=cos_config)


@router.post("", response_model=TemplateDetailOut)
def create_template(
    body: TemplateCreate,
    _user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="提示词不能为空")
    template = Template(
        prompt=body.prompt.strip(),
        model=body.model.strip() or "banana_pro",
        reference_images=json.dumps(body.reference_images or []),
        size=body.size,
        resolution=body.resolution,
        custom_size=body.custom_size.strip(),
        num_images=1,
        result_image=body.result_image,
        sort_order=body.sort_order,
    )
    db.add(template)
    db.flush()
    _sync_template_tags(db, template, body.tag_names)
    db.commit()
    db.refresh(template)
    return _serialize_template_detail(template, cos_config=get_optional_cos_config(db))


@router.put("/{template_id}", response_model=TemplateDetailOut)
def update_template(
    template_id: int,
    body: TemplateUpdate,
    _user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模版不存在")
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="提示词不能为空")

    template.prompt = body.prompt.strip()
    template.model = body.model.strip() or "banana_pro"
    template.reference_images = json.dumps(body.reference_images or [])
    template.size = body.size
    template.resolution = body.resolution
    template.custom_size = body.custom_size.strip()
    template.num_images = 1
    template.result_image = body.result_image
    template.sort_order = body.sort_order
    _sync_template_tags(db, template, body.tag_names)
    db.commit()
    db.refresh(template)
    return _serialize_template_detail(template, cos_config=get_optional_cos_config(db))


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    _user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="模版不存在")
    db.delete(template)
    db.commit()
    return {"message": "删除成功"}
