<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { message } from "ant-design-vue";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import { BugOutlined } from "@ant-design/icons-vue";
import { getAdminErrorAnalytics } from "@/api/admin";
import { getGenerationModels, getTaskScenes } from "@/api/config";
import { isSessionExpiredError } from "@/lib/authError";
import type { AdminErrorAnalytics, AdminErrorAnalyticsItem, GenerationModelOption, TaskSceneConfig } from "@/types";

type DatePreset = "today" | "3d" | "7d" | "30d";

const loading = ref(false);
const preset = ref<DatePreset | undefined>("today");
const dateRange = ref<[Dayjs, Dayjs] | null>(null);
const analytics = ref<AdminErrorAnalytics | null>(null);
const modelFilter = ref<string | undefined>(undefined);
const generationModels = ref<GenerationModelOption[]>([]);
const taskScenes = ref<TaskSceneConfig[]>([]);

const columns = [
  { title: "错误次数", dataIndex: "count", width: 120 },
  { title: "错误信息", dataIndex: "error_message" },
];

const summaryCards = computed(() => [
  {
    key: "total",
    label: "失败任务总数",
    value: analytics.value?.total_failed_tasks ?? 0,
    desc: "当前时间范围内状态为失败的任务数量",
    color: "#cf3f36",
  },
  {
    key: "distinct",
    label: "错误类型数",
    value: analytics.value?.distinct_error_messages ?? 0,
    desc: "按 error_message 聚合后的不同错误信息数量",
    color: "#d48806",
  },
]);

const modelOptions = computed(() => {
  const optionMap = new Map<string, string>();
  generationModels.value.forEach((item) => {
    optionMap.set(item.model_key, item.model_label);
  });
  taskScenes.value
    .filter((item) => item.scene_type === "image_edit")
    .forEach((item) => {
      optionMap.set(item.scene_key, item.display_name || item.scene_label);
    });
  optionMap.set("inpaint", "局部重绘");
  return Array.from(optionMap.entries()).map(([value, label]) => ({ value, label }));
});

function formatQueryDate(value?: Dayjs) {
  return value ? value.format("YYYY-MM-DDTHH:mm:ss") : undefined;
}

function applyPreset(nextPreset: DatePreset) {
  const now = dayjs();
  preset.value = nextPreset;
  if (nextPreset === "today") {
    dateRange.value = [now.startOf("day"), now.endOf("day")];
    return;
  }
  if (nextPreset === "3d") {
    dateRange.value = [now.subtract(2, "day").startOf("day"), now.endOf("day")];
    return;
  }
  if (nextPreset === "7d") {
    dateRange.value = [now.subtract(6, "day").startOf("day"), now.endOf("day")];
    return;
  }
  dateRange.value = [now.subtract(29, "day").startOf("day"), now.endOf("day")];
}

function handlePresetChange(value: DatePreset) {
  applyPreset(value);
  load();
}

function handleDateRangeChange() {
  preset.value = undefined;
  if (dateRange.value?.[0] && dateRange.value?.[1]) {
    load();
  }
}

function handleReset() {
  applyPreset("today");
  modelFilter.value = undefined;
  load();
}

async function loadModelOptions() {
  try {
    const [models, scenes] = await Promise.all([getGenerationModels(), getTaskScenes()]);
    generationModels.value = models;
    taskScenes.value = scenes;
  } catch {
    generationModels.value = [];
    taskScenes.value = [];
  }
}

async function load() {
  if (!dateRange.value?.[0] || !dateRange.value?.[1]) return;
  loading.value = true;
  try {
    analytics.value = await getAdminErrorAnalytics({
      start_date: formatQueryDate(dateRange.value[0].startOf("day")),
      end_date: formatQueryDate(dateRange.value[1].endOf("day")),
      model: modelFilter.value,
    });
  } catch (err: unknown) {
    if (isSessionExpiredError(err)) return;
    message.error("获取错误统计失败");
  } finally {
    loading.value = false;
  }
}

function getErrorRowKey(record: AdminErrorAnalytics["items"][number]) {
  return record.error_message;
}

onMounted(async () => {
  applyPreset("today");
  await loadModelOptions();
  load();
});
</script>

<template>
  <div class="warm-page motion-page-enter">
    <div class="warm-page-header motion-fade-up" style="--motion-delay: 40ms">
      <div class="warm-page-heading">
        <div class="warm-page-icon">
          <BugOutlined />
        </div>
        <div>
          <div class="warm-page-title">错误统计</div>
          <div class="warm-page-desc">查看时间范围内失败任务数量，并按 error_message 聚合错误分布。</div>
        </div>
      </div>
      <div v-if="analytics" class="page-period-chip">
        {{ analytics.range_label }}
      </div>
    </div>

    <div class="analytics-filter warm-card motion-fade-up motion-card-lift" style="--motion-delay: 120ms">
      <div class="analytics-filter-row">
        <a-range-picker
          v-model:value="dateRange"
          :placeholder="['开始日期', '结束日期']"
          class="analytics-filter-date"
          @change="handleDateRangeChange"
        />
        <a-select
          v-model:value="modelFilter"
          allow-clear
          show-search
          class="analytics-filter-select"
          placeholder="全部模型"
          :options="modelOptions"
          option-filter-prop="label"
          @change="load"
        />
        <div class="analytics-filter-panel-compact">
          <a-radio-group
            :value="preset"
            class="analytics-segmented-group analytics-segmented-group-secondary"
            button-style="solid"
            @update:value="handlePresetChange"
          >
            <a-radio-button value="today">今日</a-radio-button>
            <a-radio-button value="3d">近 3 天</a-radio-button>
            <a-radio-button value="7d">近 7 天</a-radio-button>
            <a-radio-button value="30d">近 30 天</a-radio-button>
          </a-radio-group>
        </div>
        <a-button type="primary" class="analytics-action-btn" :loading="loading" @click="load">查询</a-button>
        <a-button class="analytics-action-btn analytics-action-btn-secondary" @click="handleReset">重置</a-button>
      </div>
    </div>

    <div class="summary-grid">
      <div
        v-for="(item, index) in summaryCards"
        :key="item.key"
        class="summary-card warm-card motion-card-lift motion-fade-up"
        :style="{ '--motion-delay': `${160 + index * 40}ms` }"
      >
        <div class="summary-card-head">
          <span class="summary-card-label">{{ item.label }}</span>
          <span class="summary-card-dot" :style="{ background: item.color }" />
        </div>
        <div class="summary-card-value" :style="{ color: item.color }">{{ item.value }}</div>
        <div class="summary-card-desc">{{ item.desc }}</div>
      </div>
    </div>

    <div class="warm-card warm-table-card motion-card-lift motion-fade-up" style="--motion-delay: 260ms">
      <div class="table-card-head">
        <div>
          <div class="table-card-title">错误明细</div>
          <div class="table-card-desc">按 `error_message` 聚合展示每种错误发生次数。</div>
        </div>
      </div>
      <a-table
        :columns="columns"
        :data-source="analytics?.items || []"
        :loading="loading"
        :pagination="false"
        :row-key="getErrorRowKey"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'count'">
            <span class="count-badge">{{ record.count }}</span>
          </template>
          <template v-else-if="column.dataIndex === 'error_message'">
            <div class="error-message-cell">{{ record.error_message }}</div>
          </template>
        </template>
        <template #emptyText>
          <a-empty description="当前时间范围内暂无失败错误记录" />
        </template>
      </a-table>
    </div>
  </div>
</template>

<style scoped lang="scss">
.analytics-filter {
  margin-bottom: 16px;
}

.page-period-chip {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 253, 248, 0.92);
  border: 1px solid rgba(240, 223, 190, 0.95);
  color: #8c7458;
  font-size: 13px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.summary-card {
  min-height: 116px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  justify-content: space-between;
}

.summary-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.summary-card-label {
  color: #8c7458;
  font-size: 13px;
  font-weight: 700;
}

.summary-card-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  box-shadow: 0 0 0 4px rgba(255, 193, 90, 0.14);
}

.summary-card-value {
  font-size: 30px;
  line-height: 1.1;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.summary-card-desc {
  color: #9a805b;
  font-size: 12px;
  line-height: 1.5;
}

.table-card-head {
  padding: 18px 20px 14px;
  border-bottom: 1px solid rgba(240, 223, 190, 0.9);
  background: linear-gradient(180deg, rgba(255, 250, 240, 0.88), rgba(255, 255, 255, 0.2));
}

.table-card-title {
  color: #5d4526;
  font-size: 16px;
  font-weight: 700;
}

.table-card-desc {
  margin-top: 8px;
  color: #9a805b;
  font-size: 12px;
  line-height: 1.5;
}

.count-badge {
  display: inline-flex;
  min-width: 34px;
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(255, 242, 239, 0.96);
  color: #cf3f36;
  font-weight: 700;
  justify-content: center;
}

.error-message-cell {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
  color: var(--theme-text);
}

.analytics-filter-select {
  width: 336px;
}

@media (max-width: 768px) {
  .analytics-filter-row {
    align-items: stretch;
  }

  .analytics-filter-select,
  .analytics-filter-date,
  .analytics-action-btn {
    width: 100%;
  }
}
</style>
