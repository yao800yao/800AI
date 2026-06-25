<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { message, Modal } from "ant-design-vue";
import {
  DeleteOutlined,
  EditOutlined,
  PictureOutlined,
  PlusOutlined,
  TagsOutlined,
  UploadOutlined,
} from "@ant-design/icons-vue";
import { uploadReferenceImage } from "@/api/upload";
import { getGenerationModels } from "@/api/config";
import {
  createTemplateTag,
  createTemplate,
  deleteTemplateTag,
  deleteTemplate,
  getTemplateDetail,
  listAdminTemplates,
  listTemplateTags,
  updateTemplateTag,
  updateTemplate,
  type TemplatePayload,
} from "@/api/templates";
import { resolveImageUrl } from "@/api/images";
import type { CreativeTemplate, GenerationModelOption, TemplateTag } from "@/types";

const templates = ref<CreativeTemplate[]>([]);
const tags = ref<TemplateTag[]>([]);
const modelOptions = ref<GenerationModelOption[]>([]);
const loading = ref(false);
const modalOpen = ref(false);
const saving = ref(false);
const editingId = ref<number | null>(null);
const activeParentId = ref<number | null>(null);
const activeTagId = ref<number | null>(null);
const tagManageOpen = ref(false);
const savingTag = ref(false);
const editingTag = ref<TemplateTag | null>(null);

const refInput = ref<HTMLInputElement | null>(null);
const resultInput = ref<HTMLInputElement | null>(null);
const refUploading = ref(false);
const resultUploading = ref(false);

const form = reactive<TemplatePayload>({
  prompt: "",
  model: "banana_pro",
  reference_images: [],
  num_images: 1,
  size: "9:16",
  resolution: "2K",
  custom_size: "",
  result_image: "",
  sort_order: 0,
  tag_ids: [],
});

const columns = [
  { title: "结果图", dataIndex: "result_image", width: 110 },
  { title: "提示词", dataIndex: "prompt", width: 280, ellipsis: true },
  { title: "标签", key: "tags", width: 220 },
  { title: "排序", dataIndex: "sort_order", width: 90 },
  { title: "参数", key: "meta", width: 180 },
  { title: "创建时间", dataIndex: "created_at", width: 180 },
  { title: "操作", key: "action", width: 160 },
];

const sizeOptions = [
  { label: "1:1", value: "1:1" },
  { label: "2:3", value: "2:3" },
  { label: "3:2", value: "3:2" },
  { label: "3:4", value: "3:4" },
  { label: "4:3", value: "4:3" },
  { label: "9:16", value: "9:16" },
  { label: "16:9", value: "16:9" },
];

const resolutionOptions = [
  { label: "1K", value: "1K" },
  { label: "2K", value: "2K" },
  { label: "4K", value: "4K" },
];

const customSizeOptions = computed(() => (
  selectedModelOption.value?.custom_size_options?.length
    ? selectedModelOption.value.custom_size_options
    : []
));

const selectedModelOption = computed(() => modelOptions.value.find((item) => item.model_key === form.model) || null);
const hideResolution = computed(() => !!selectedModelOption.value?.hide_resolution);
const hideCustomSize = computed(() => !!selectedModelOption.value?.hide_custom_size);
const filteredTemplates = computed(() => {
  if (activeTagId.value !== null) {
    return templates.value.filter((item) => item.tags.some((tag) => tag.id === activeTagId.value));
  }
  if (activeParentId.value !== null) {
    const childIds = new Set(childTags.value.map((tag) => tag.id));
    if (childIds.size) {
      return templates.value.filter((item) => item.tags.some((tag) => childIds.has(tag.id)));
    }
    return templates.value.filter((item) => item.tags.some((tag) => tag.id === activeParentId.value));
  }
  return templates.value;
});

const renameForm = reactive({
  name: "",
  parent_id: null as number | null,
  sort_order: 0,
});

function sortTags(list: TemplateTag[]) {
  return [...list].sort(
    (a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0) || a.name.localeCompare(b.name, "zh-CN")
  );
}

const parentTags = computed(() => sortTags(tags.value.filter((tag) => tag.parent_id == null)));
const childTags = computed(() => {
  if (activeParentId.value == null) return [];
  return sortTags(tags.value.filter((tag) => tag.parent_id === activeParentId.value));
});
const showChildTags = computed(() => childTags.value.length > 0);
const tagGroups = computed(() =>
  parentTags.value.map((parent) => ({
    parent,
    children: sortTags(tags.value.filter((tag) => tag.parent_id === parent.id)),
  }))
);
const parentTagOptions = computed(() =>
  parentTags.value.map((tag) => ({ label: tag.name, value: tag.id }))
);
const tagType = ref<"parent" | "child">("parent");
const editingTagHasChildren = computed(() => {
  if (!editingTag.value) return false;
  return tags.value.some((tag) => tag.parent_id === editingTag.value?.id);
});
const assignableTagOptions = computed(() =>
  parentTags.value.flatMap((parent) => {
    const children = tags.value.filter((tag) => tag.parent_id === parent.id);
    return children.map((child) => ({
      label: `${parent.name} / ${child.name}`,
      value: child.id,
    }));
  })
);
const tagOptions = computed(() => assignableTagOptions.value);

function resetForm() {
  editingId.value = null;
  form.prompt = "";
  form.model = modelOptions.value[0]?.model_key || "banana_pro";
  form.reference_images = [];
  form.num_images = 1;
  form.size = "9:16";
  form.resolution = "2K";
  form.custom_size = "";
  form.result_image = "";
  form.sort_order = 0;
  form.tag_ids = [];
}

function resetTagForm() {
  editingTag.value = null;
  renameForm.name = "";
  renameForm.parent_id = null;
  renameForm.sort_order = 0;
  tagType.value = "parent";
}

async function load() {
  loading.value = true;
  try {
    templates.value = await listAdminTemplates();
  } catch {
    message.error("获取模版列表失败");
  } finally {
    loading.value = false;
  }
}

async function loadTags() {
  try {
    tags.value = await listTemplateTags();
    if (activeTagId.value !== null && !tags.value.some((tag) => tag.id === activeTagId.value)) {
      activeTagId.value = null;
    }
    if (activeParentId.value !== null && !tags.value.some((tag) => tag.id === activeParentId.value)) {
      activeParentId.value = null;
    }
  } catch {
    // ignore
  }
}

async function loadModels() {
  try {
    modelOptions.value = await getGenerationModels();
    if (!modelOptions.value.some((item) => item.model_key === form.model) && modelOptions.value.length) {
      form.model = modelOptions.value[0].model_key;
    }
  } catch {
    // ignore
  }
}

onMounted(() => {
  load();
  loadTags();
  loadModels();
});

function openCreate() {
  resetForm();
  modalOpen.value = true;
}

function openTagManage() {
  resetTagForm();
  tagManageOpen.value = true;
}

function openRenameTag(tag: TemplateTag) {
  editingTag.value = tag;
  renameForm.name = tag.name;
  renameForm.parent_id = tag.parent_id ?? null;
  renameForm.sort_order = tag.sort_order ?? 0;
  tagType.value = tag.parent_id == null ? "parent" : "child";
}

function selectParent(parentId: number | null) {
  activeParentId.value = parentId;
  activeTagId.value = null;
}

function selectChild(tagId: number | null) {
  activeTagId.value = tagId;
}

function formatTagLabel(tag: TemplateTag) {
  if (tag.parent_id == null) return tag.name;
  const parent = tags.value.find((item) => item.id === tag.parent_id);
  return parent ? `${parent.name} / ${tag.name}` : tag.name;
}

async function openEdit(item: CreativeTemplate) {
  try {
    const detail = await getTemplateDetail(item.id);
    editingId.value = item.id;
    form.prompt = detail.prompt;
    form.model = detail.model || modelOptions.value[0]?.model_key || "banana_pro";
    form.reference_images = [...detail.reference_images];
    form.num_images = 1;
    form.size = detail.size;
    form.resolution = detail.resolution;
    form.custom_size = detail.custom_size || "";
    form.result_image = detail.result_image;
    form.sort_order = detail.sort_order ?? 0;
    form.tag_ids = detail.tags.map((tag) => tag.id);
    modalOpen.value = true;
  } catch {
    message.error("获取模版详情失败");
  }
}

async function handleSave() {
  if (!form.prompt.trim()) {
    message.warning("请输入提示词");
    return;
  }
  if (!form.result_image) {
    message.warning("请上传结果图");
    return;
  }
  saving.value = true;
  try {
    const payload: TemplatePayload = {
      prompt: form.prompt.trim(),
      model: form.model,
      reference_images: [...form.reference_images],
      num_images: 1,
      size: form.size,
      resolution: hideResolution.value ? "" : form.resolution,
      custom_size: hideCustomSize.value ? "" : form.custom_size,
      result_image: form.result_image,
      sort_order: Number.isFinite(form.sort_order) ? form.sort_order : 0,
      tag_ids: [...form.tag_ids],
    };
    if (editingId.value) await updateTemplate(editingId.value, payload);
    else await createTemplate(payload);
    message.success(editingId.value ? "模版更新成功" : "模版创建成功");
    modalOpen.value = false;
    resetForm();
    load();
    loadTags();
  } catch (err: any) {
    message.error(err.response?.data?.detail || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function handleSaveTag() {
  const name = renameForm.name.trim();
  if (!name) {
    message.warning("请输入标签名称");
    return;
  }
  if (tagType.value === "child" && !renameForm.parent_id) {
    message.warning("请选择所属大标签");
    return;
  }
  savingTag.value = true;
  try {
    const payload = {
      name,
      parent_id: editingTagHasChildren.value || tagType.value === "parent" ? null : renameForm.parent_id,
      sort_order: renameForm.sort_order,
    };
    if (editingTag.value) {
      await updateTemplateTag(editingTag.value.id, payload);
      message.success("标签更新成功");
      await Promise.all([load(), loadTags()]);
    } else {
      await createTemplateTag(payload);
      message.success("标签创建成功");
      await loadTags();
    }
    resetTagForm();
  } catch (err: any) {
    message.error(err.response?.data?.detail || (editingTag.value ? "标签更新失败" : "标签创建失败"));
  } finally {
    savingTag.value = false;
  }
}

function handleDelete(item: CreativeTemplate) {
  Modal.confirm({
    title: "确认删除该模版？",
    centered: true,
    async onOk() {
      await deleteTemplate(item.id);
      message.success("删除成功");
      load();
      loadTags();
    },
  });
}

function handleDeleteTag(tag: TemplateTag) {
  Modal.confirm({
    title: `确认删除标签「${tag.name}」？`,
    content: "删除后会同步移除该标签与模板的关联关系。",
    centered: true,
    async onOk() {
      await deleteTemplateTag(tag.id);
      message.success("标签删除成功");
      await Promise.all([load(), loadTags()]);
    },
  });
}

function triggerRefUpload() {
  refInput.value?.click();
}

function triggerResultUpload() {
  resultInput.value?.click();
}

async function handleRefUpload(e: Event) {
  const input = e.target as HTMLInputElement;
  const files = Array.from(input.files || []);
  if (!files.length) return;
  refUploading.value = true;
  try {
    for (const file of files) {
      const res = await uploadReferenceImage(file, "template");
      form.reference_images.push(res.url);
    }
    message.success("参考图上传成功");
  } catch {
    message.error("参考图上传失败");
  } finally {
    refUploading.value = false;
    input.value = "";
  }
}

async function handleResultUpload(e: Event) {
  const input = e.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  resultUploading.value = true;
  try {
    const res = await uploadReferenceImage(file, "template");
    form.result_image = res.url;
    message.success("结果图上传成功");
  } catch {
    message.error("结果图上传失败");
  } finally {
    resultUploading.value = false;
    input.value = "";
  }
}

function removeRef(index: number) {
  form.reference_images.splice(index, 1);
}

function fmtTime(t: string) {
  return t ? new Date(t).toLocaleString("zh-CN") : "-";
}
</script>

<template>
  <div class="warm-page motion-page-enter">
    <div class="warm-page-header motion-fade-up" style="--motion-delay: 40ms">
      <div class="warm-page-heading">
        <div class="warm-page-icon">
          <PictureOutlined />
        </div>
        <div>
          <div class="warm-page-title">模版管理</div>
          <div class="warm-page-desc">维护创意模版内容、标签和展示结果图。</div>
        </div>
      </div>
      <div class="page-actions">
        <a-button type="primary" class="warm-primary-btn" @click="openTagManage">
          <template #icon><TagsOutlined /></template>
          标签管理
        </a-button>
        <a-button type="primary" class="warm-primary-btn" @click="openCreate">
          <template #icon><PlusOutlined /></template>
          新增模版
        </a-button>
      </div>
    </div>

    <div class="tag-filter-row motion-fade-up" style="--motion-delay: 120ms">
      <button
        type="button"
        class="tag-nav-item"
        :class="{ active: activeParentId === null && activeTagId === null }"
        @click="selectParent(null)"
      >
        全部模版
      </button>
      <button
        v-for="tag in parentTags"
        :key="tag.id"
        type="button"
        class="tag-nav-item"
        :class="{ active: activeParentId === tag.id && activeTagId === null }"
        @click="selectParent(tag.id)"
      >
        {{ tag.name }}
      </button>
    </div>

    <div v-if="showChildTags" class="tag-filter-row tag-filter-row-child motion-fade-up" style="--motion-delay: 160ms">
      <button
        type="button"
        class="tag-nav-item tag-nav-item-child"
        :class="{ active: activeTagId === null }"
        @click="selectChild(null)"
      >
        全部
      </button>
      <button
        v-for="tag in childTags"
        :key="tag.id"
        type="button"
        class="tag-nav-item tag-nav-item-child"
        :class="{ active: activeTagId === tag.id }"
        @click="selectChild(tag.id)"
      >
        {{ tag.name }}
      </button>
    </div>

    <div class="warm-card warm-table-card motion-fade-up motion-card-lift" style="--motion-delay: 200ms">
      <a-table
        :columns="columns"
        :data-source="filteredTemplates"
        :loading="loading"
        row-key="id"
        :pagination="false"
        :scroll="{ x: 1220 }"
        class="admin-mobile-table"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'result_image'">
            <div class="thumb-box">
              <img v-if="record.result_image" :src="resolveImageUrl(record.result_image_thumb || record.result_image)" alt="结果图" loading="lazy" />
            </div>
          </template>
          <template v-else-if="column.key === 'tags'">
            <div class="tag-list">
              <a-tag v-for="tag in record.tags" :key="tag.id" class="warm-tag">{{ formatTagLabel(tag) }}</a-tag>
            </div>
          </template>
          <template v-else-if="column.dataIndex === 'sort_order'">
            {{ record.sort_order ?? 0 }}
          </template>
          <template v-else-if="column.key === 'meta'">
            <div class="meta-cell">
              {{ record.model || "-" }} / {{ record.size }}
              <span v-if="record.resolution"> / {{ record.resolution }}</span>
              <span v-if="record.custom_size"> / {{ record.custom_size }}</span>
            </div>
          </template>
          <template v-else-if="column.dataIndex === 'created_at'">
            {{ fmtTime(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'action'">
            <div class="table-actions">
              <a-button type="link" size="small" class="template-action-btn template-action-btn-primary" @click="openEdit(record)">
                <template #icon><EditOutlined /></template>
                编辑
              </a-button>
              <a-divider type="vertical" />
              <a-button type="link" danger size="small" class="template-action-btn template-action-btn-danger" @click="handleDelete(record)">
                <template #icon><DeleteOutlined /></template>
                删除
              </a-button>
            </div>
          </template>
        </template>
      </a-table>
    </div>

    <a-modal
      v-model:open="modalOpen"
      :title="editingId ? '编辑模版' : '新增模版'"
      :confirm-loading="saving"
      :ok-button-props="{ class: 'warm-primary-btn' }"
      :cancel-button-props="{ class: 'warm-secondary-btn' }"
      ok-text="保存"
      cancel-text="取消"
      centered
      :width="760"
      @ok="handleSave"
      @cancel="resetForm"
    >
      <a-form layout="vertical" style="margin-top: 16px">
        <a-form-item label="提示词">
          <a-textarea v-model:value="form.prompt" class="warm-textarea" :rows="5" :maxlength="2000" show-count />
        </a-form-item>

        <div class="form-grid">
          <a-form-item label="模型">
            <a-select v-model:value="form.model" class="warm-select" placeholder="请选择模型">
              <a-select-option v-for="model in modelOptions" :key="model.model_key" :value="model.model_key">
                {{ model.model_label }}
              </a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="宽高比">
            <a-select v-model:value="form.size" class="warm-select" :options="sizeOptions" />
          </a-form-item>
          <a-form-item label="排序值">
            <a-input-number v-model:value="form.sort_order" class="warm-input-number" :min="0" :precision="0" />
          </a-form-item>
          <a-form-item v-if="!hideResolution" label="分辨率">
            <a-select v-model:value="form.resolution" class="warm-select" :options="resolutionOptions" />
          </a-form-item>
          <a-form-item v-if="!hideCustomSize" label="自定义分辨率">
            <a-select
              v-model:value="form.custom_size"
              class="warm-select"
              :options="customSizeOptions"
              allow-clear
              placeholder="可选，带入 {{ custom_size }}"
            />
          </a-form-item>
          <a-form-item label="所属标签">
            <a-select
              v-model:value="form.tag_ids"
              class="warm-select"
              mode="multiple"
              :options="tagOptions"
              placeholder="选择小标签"
            />
          </a-form-item>
        </div>

        <a-form-item label="结果图">
          <div class="result-upload">
            <div class="result-preview">
              <img v-if="form.result_image" :src="form.result_image" alt="结果图" />
              <div v-else class="result-placeholder">请上传结果图</div>
            </div>
            <input ref="resultInput" type="file" accept="image/*" hidden @change="handleResultUpload" />
            <a-button class="template-secondary-btn" :loading="resultUploading" @click="triggerResultUpload">
              <template #icon><UploadOutlined /></template>
              上传结果图
            </a-button>
          </div>
        </a-form-item>

        <a-form-item label="参考图片（可选）" style="margin-bottom: 0">
          <input ref="refInput" type="file" accept="image/*" multiple hidden @change="handleRefUpload" />
          <div class="ref-grid">
            <div v-for="(url, idx) in form.reference_images" :key="url + idx" class="ref-item">
              <img :src="url" alt="参考图" />
              <a-button type="text" danger shape="circle" class="ref-remove" @click="removeRef(idx)">
                <template #icon><DeleteOutlined /></template>
              </a-button>
            </div>
            <a-button class="ref-add template-secondary-btn" :loading="refUploading" @click="triggerRefUpload">
              <template #icon><UploadOutlined /></template>
              上传参考图
            </a-button>
          </div>
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="tagManageOpen"
      title="标签管理"
      :confirm-loading="savingTag"
      :ok-button-props="{ class: 'warm-primary-btn' }"
      :cancel-button-props="{ class: 'warm-secondary-btn' }"
      ok-text="提交"
      cancel-text="取消"
      centered
      :width="760"
      @ok="handleSaveTag"
      @cancel="resetTagForm"
    >
      <a-form layout="vertical" style="margin-top: 16px">
        <a-form-item :label="editingTag ? '编辑标签' : '新增标签'">
          <div class="tag-create-box">
            <a-input
              v-model:value="renameForm.name"
              class="warm-input"
              :maxlength="50"
              :placeholder="editingTag ? '请输入新的标签名称' : '输入标签名称'"
              @pressEnter="handleSaveTag"
            />
            <a-input-number
              v-model:value="renameForm.sort_order"
              class="warm-input-number"
              :min="0"
              :precision="0"
              placeholder="排序"
            />
            <a-button v-if="editingTag" class="template-secondary-btn" @click="resetTagForm">取消编辑</a-button>
          </div>
        </a-form-item>
        <a-form-item v-if="!editingTagHasChildren" label="标签类型">
          <a-radio-group v-model:value="tagType">
            <a-radio value="parent">大标签</a-radio>
            <a-radio value="child">小标签</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item
          v-if="!editingTagHasChildren && tagType === 'child'"
          label="所属大标签"
        >
          <a-select
            v-model:value="renameForm.parent_id"
            class="warm-select"
            :options="parentTagOptions"
            placeholder="请选择大标签"
          />
        </a-form-item>
      </a-form>

      <div v-if="tagGroups.length" class="tag-manage-list">
        <div v-for="group in tagGroups" :key="group.parent.id" class="tag-manage-group">
          <div class="tag-manage-item tag-manage-item-parent">
            <div class="tag-manage-main">
              <a-tag class="warm-tag">{{ group.parent.name }}</a-tag>
              <span class="tag-manage-type">大标签</span>
              <span class="tag-manage-count">关联 {{ group.parent.template_count ?? 0 }} 个模版</span>
            </div>
            <div class="tag-manage-actions">
              <a-button type="link" size="small" class="template-action-btn template-action-btn-primary" @click="openRenameTag(group.parent)">编辑</a-button>
              <a-divider type="vertical" />
              <a-button type="link" danger size="small" class="template-action-btn template-action-btn-danger" @click="handleDeleteTag(group.parent)">删除</a-button>
            </div>
          </div>
          <div
            v-for="child in group.children"
            :key="child.id"
            class="tag-manage-item tag-manage-item-child"
          >
            <div class="tag-manage-main">
              <a-tag class="warm-tag">{{ child.name }}</a-tag>
              <span class="tag-manage-type">小标签</span>
              <span class="tag-manage-count">关联 {{ child.template_count ?? 0 }} 个模版</span>
            </div>
            <div class="tag-manage-actions">
              <a-button type="link" size="small" class="template-action-btn template-action-btn-primary" @click="openRenameTag(child)">编辑</a-button>
              <a-divider type="vertical" />
              <a-button type="link" danger size="small" class="template-action-btn template-action-btn-danger" @click="handleDeleteTag(child)">删除</a-button>
            </div>
          </div>
        </div>
      </div>
      <a-empty v-else class="warm-empty" description="暂无标签，可先新增标签" />
    </a-modal>
  </div>
</template>

<style scoped lang="scss">
.page-actions {
  display: flex;
  gap: 12px;
}

.tag-manage-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.tag-manage-title {
  color: #4c341a;
  font-size: 16px;
  font-weight: 700;
}

.tag-manage-desc {
  margin-top: 6px;
  color: #8d7457;
  font-size: 13px;
}

.tag-create-box {
  display: flex;
  gap: 12px;
  width: min(100%, 420px);
}

.tag-filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  margin-bottom: 16px;
}

.tag-filter-row-child {
  margin-top: -8px;
}

.tag-nav-item {
  position: relative;
  border: 0;
  background: transparent;
  padding: 0 0 6px;
  color: #6f6254;
  font-size: 15px;
  line-height: 1.4;
  cursor: pointer;

  &.active {
    color: #1f160d;
    font-weight: 700;
  }

  &.active::after {
    content: "";
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    height: 2px;
    border-radius: 999px;
    background: #1f160d;
  }
}

.tag-nav-item-child {
  font-size: 14px;
  color: #85786a;
}

.tag-manage-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 12px;
  margin-bottom: 12px;
  border-bottom: 1px solid rgba(140, 108, 66, 0.12);
}

.tag-manage-group:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: 0;
}

.tag-manage-item-child {
  margin-left: 18px;
}

.tag-manage-type {
  color: #9a8568;
  font-size: 12px;
}

.manage-filter-tag {
  cursor: pointer;
  border-radius: 999px;
  padding: 6px 12px;
  font-weight: 600;

  &.active {
    color: #8a5400;
    background: linear-gradient(180deg, #fff0cc, #ffe2a9);
    border-color: #f0c46d;
  }
}

.tag-manage-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.tag-manage-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid #f0dfbe;
  background: #fffaf2;
}

.tag-manage-main {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  min-width: 0;
}

.tag-manage-count {
  color: #8d7457;
  font-size: 13px;
}

.tag-manage-actions {
  flex-shrink: 0;
}

.thumb-box {
  width: 72px;
  height: 72px;
  border-radius: 12px;
  overflow: hidden;
  background: #fff8ec;
  border: 1px solid #f0dfbe;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.meta-cell {
  color: #6b5436;
  font-weight: 600;
}

.table-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.table-actions :deep(.ant-divider-vertical),
.tag-manage-actions :deep(.ant-divider-vertical) {
  margin-inline: 2px;
  border-inline-start-color: #efd7b1;
}

.template-action-btn {
  height: 30px;
  padding-inline: 10px;
  border-radius: 10px;
  font-weight: 600;
}

.template-action-btn.template-action-btn-primary {
  color: #c7770d !important;
  background: #fff4df !important;
}

.template-action-btn.template-action-btn-danger {
  color: #d6574b !important;
  background: #fff1ef !important;
}

.template-action-btn:hover,
.template-action-btn:focus {
  opacity: 0.92;
}

.template-secondary-btn {
  border-color: #efc784 !important;
  background: #fff7e8 !important;
  color: #b16d10 !important;
  border-radius: 12px !important;
  font-weight: 600;
}

.template-secondary-btn:hover,
.template-secondary-btn:focus {
  border-color: #e1a64a !important;
  background: #fff0d3 !important;
  color: #c7770d !important;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.result-upload {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.result-preview {
  width: 132px;
  height: 132px;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid var(--theme-panel-border);
  background: var(--theme-panel-bg-soft);
  flex-shrink: 0;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
}

.result-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-size: 13px;
}

.ref-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.ref-item {
  position: relative;
  width: 84px;
  height: 84px;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid var(--theme-panel-border);
  background: var(--theme-panel-bg-soft);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
}

.ref-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  background: rgba(var(--theme-surface-strong-rgb), 0.92) !important;
  border: 1px solid var(--theme-panel-border) !important;
  color: #d6574b !important;
}

html:is([data-theme="dark"], [data-theme="midnight"]) .warm-page .template-action-btn.template-action-btn-primary {
  background: var(--theme-panel-bg-strong) !important;
  color: var(--theme-accent-text) !important;
}

html:is([data-theme="dark"], [data-theme="midnight"]) .warm-page .template-action-btn.template-action-btn-danger {
  background: rgba(185, 56, 42, 0.12) !important;
  color: #de8f84 !important;
}

html:is([data-theme="dark"], [data-theme="midnight"]) .warm-page .ref-remove {
  background: rgba(var(--theme-surface-strong-rgb), 0.92) !important;
  border-color: var(--theme-panel-border) !important;
  color: #de8f84 !important;
}

.ref-add {
  height: 84px;
  min-width: 120px;
  border-radius: 14px;
}

@media (max-width: 720px) {
  :deep(.admin-mobile-table .ant-table-content) {
    overflow-x: auto !important;
  }

  .page-actions,
  .tag-manage-header,
  .tag-create-box {
    flex-direction: column;
  }

  .tag-create-box {
    width: 100%;
  }

  .tag-manage-list {
    grid-template-columns: 1fr;
  }

  .tag-manage-item {
    align-items: flex-start;
    flex-direction: column;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .result-upload {
    flex-direction: column;
  }
}
</style>
