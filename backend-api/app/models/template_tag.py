from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import backref, relationship

from app.database import Base


class TemplateTag(Base):
    __tablename__ = "template_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("template_tags.id", ondelete="CASCADE"), nullable=True, index=True)
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime, server_default=func.now())

    parent = relationship(
        "TemplateTag",
        remote_side=[id],
        backref=backref("children", lazy="selectin"),
    )
    template_relations = relationship(
        "TemplateTagRelation",
        back_populates="tag",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
