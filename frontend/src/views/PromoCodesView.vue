<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { GiftOutlined, CopyOutlined, UserAddOutlined, UndoOutlined } from "@ant-design/icons-vue";
import { message } from "ant-design-vue";
import dayjs from "dayjs";
import { useRouter } from "vue-router";

import {
  createPromoCode,
  getMyPromoCodes,
  getMyPromoReferralsWithFilters,
  getMyPromoReferralActivities,
  updatePromoCodePlatform,
} from "@/api/auth";
import { useAuthStore } from "@/stores/auth";
import type {
  PromoCodeItem,
  PromoCodeSummary,
  PromoReferralActivityItem,
  PromoReferralItem,
} from "@/types";

const auth = useAuthStore();
const router = useRouter();

const loading = ref(false);
const createLoading = ref(false);
const editingPromoId = ref<number | null>(null);
const editPlatformName = ref("");
const saveEditingLoading = ref(false);
const summary = ref<PromoCodeSummary>({
  total_referrals: 0,
  used_code_count: 0,
  rewarded_registrations: 0,
});
const promoCodes = ref<PromoCodeItem[]>([]);
const referrals = ref<PromoReferralItem[]>([]);
const activities = ref<PromoReferralActivityItem[]>([]);
const createForm = reactive({
  platformName: "",
});
function getBeijingDateString(date = new Date()) {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function getBeijingDayRange(): [dayjs.Dayjs, dayjs.Dayjs] {
  const dateStr = getBeijingDateString();
  return [dayjs(`${dateStr}T00:00:00`), dayjs(`${dateStr}T23:59:59`)];
}

function formatQueryDate(value?: dayjs.Dayjs) {
  return value ? value.format("YYYY-MM-DDTHH:mm:ss") : undefined;
}

const referralFilters = reactive({
  keyword: "",
  platformName: undefined as string | undefined,
  dateRange: getBeijingDayRange(),
});

const isWhitelisted = computed(() => auth.user?.is_whitelisted === true);

const promoColumns = [
  { title: "推广码", dataIndex: "code", width: 180 },
  { title: "平台", dataIndex: "platform_name", width: 220 },
  { title: "使用人数", dataIndex: "referral_count", width: 120 },
  { title: "状态", dataIndex: "status", width: 120 },
  { title: "创建时间", dataIndex: "created_at", width: 180 },
  { title: "操作", key: "actions", width: 180, fixed: "right" as const },
];

const referralColumns = [
  { title: "用户", key: "user", width: "22%" },
  { title: "推广码", dataIndex: "promo_code", ellipsis: true },
  { title: "来源平台", dataIndex: "platform_name", ellipsis: true },
  { title: "奖励积分", dataIndex: "reward_credits", width: 88 },
  { title: "注册时间", dataIndex: "registered_at", width: 168 },
];

const activityColumns = [
  { title: "用户", key: "user", width: "22%" },
  { title: "类型", dataIndex: "activity_type", width: 100 },
  { title: "积分", dataIndex: "credits", width: 72 },
  { title: "金额", dataIndex: "amount_yuan", width: 96 },
  { title: "订单号/兑换码", dataIndex: "activity_ref", ellipsis: true },
  { title: "发生时间", dataIndex: "occurred_at", width: 168 },
];

function formatTime(value?: string | null) {
  return value ? dayjs(value).format("YYYY-MM-DD HH:mm:ss") : "-";
}

async function copyPromoCode(code: string) {
  try {
    await navigator.clipboard.writeText(code);
    message.success("推广码已复制");
  } catch {
    message.error("复制失败，请重试");
  }
}

function startEditPromo(record: PromoCodeItem) {
  editingPromoId.value = record.id;
  editPlatformName.value = record.platform_name;
}

function cancelEditPromo() {
  editingPromoId.value = null;
  editPlatformName.value = "";
}

async function saveEditPromo(record: PromoCodeItem) {
  const normalizedName = editPlatformName.value.trim();
  if (!normalizedName) {
    message.warning("请输入平台名称");
    return;
  }
  saveEditingLoading.value = true;
  try {
    const res = await updatePromoCodePlatform(record.id, normalizedName);
    summary.value = res.summary;
    promoCodes.value = res.items;
    message.success("平台已更新");
    cancelEditPromo();
  } catch (err: any) {
    message.error(err.response?.data?.detail || "更新平台失败");
  } finally {
    saveEditingLoading.value = false;
  }
}

async function loadData() {
  if (!isWhitelisted.value) return;
  loading.value = true;
  try {
    const params = {
      keyword: referralFilters.keyword.trim() || undefined,
      platform_name: referralFilters.platformName,
      start_date: formatQueryDate(referralFilters.dateRange?.[0].startOf("day")),
      end_date: formatQueryDate(referralFilters.dateRange?.[1].endOf("day")),
    };
    const [codesRes, referralsRes, activitiesRes] = await Promise.all([
      getMyPromoCodes(),
      getMyPromoReferralsWithFilters(params),
      getMyPromoReferralActivities(params),
    ]);
    summary.value = codesRes.summary;
    promoCodes.value = codesRes.items;
    referrals.value = referralsRes.items;
    activities.value = activitiesRes.items;
  } catch (err: any) {
    message.error(err.response?.data?.detail || "获取推广数据失败");
  } finally {
    loading.value = false;
  }
}

async function handleCreatePromoCode() {
  if (!createForm.platformName.trim()) {
    message.warning("请输入平台名称");
    return;
  }
  createLoading.value = true;
  try {
    const res = await createPromoCode(createForm.platformName.trim());
    summary.value = res.summary;
    promoCodes.value = res.items;
    createForm.platformName = "";
    await loadData();
    message.success("推广码创建成功");
  } catch (err: any) {
    message.error(err.response?.data?.detail || "创建推广码失败");
  } finally {
    createLoading.value = false;
  }
}

function handleReset() {
  createForm.platformName = "";
}

function handleSearch() {
  void loadData();
}

function handleResetFilters() {
  referralFilters.keyword = "";
  referralFilters.platformName = undefined;
  referralFilters.dateRange = getBeijingDayRange();
  void loadData();
}

onMounted(async () => {
  if (!auth.isLoggedIn) {
    await router.replace("/");
    return;
  }
  if (!isWhitelisted.value) return;
  await loadData();
});
</script>

<template>
  <div class="warm-page motion-page-enter promo-page">
    <div class="warm-page-header motion-fade-up" style="--motion-delay: 40ms">
      <div class="warm-page-heading">
        <div class="warm-page-icon">
          <GiftOutlined />
        </div>
        <div>
          <div class="warm-page-title">我的推广码</div>
          <div class="warm-page-desc">按不同平台创建推广码，查看推广用户和基础转化数据。</div>
        </div>
      </div>
    </div>

    <div v-if="!isWhitelisted" class="warm-card promo-empty motion-fade-up motion-card-lift" style="--motion-delay: 120ms">
      当前账号不是白名单用户，暂不可使用推广码功能。
    </div>

    <template v-else>
      <div class="promo-top-row motion-fade-up" style="--motion-delay: 120ms">
        <div class="warm-card promo-stat-card motion-card-lift">
          <span>推广注册人数</span>
          <strong>{{ summary.total_referrals }}</strong>
          <em>当前统计与奖励发放人数保持一致</em>
        </div>

        <div class="warm-card promo-create-card motion-card-lift">
        <div class="promo-create-header">
          <div>
            <div class="promo-create-title">新增推广码</div>
            <div class="promo-create-desc">为不同渠道单独创建推广码，便于区分来源。</div>
          </div>
        </div>
        <div class="promo-create-form">
          <a-input
            v-model:value="createForm.platformName"
            placeholder="例如：小红书、抖音、公众号"
            :maxlength="50"
            @press-enter="handleCreatePromoCode"
          />
          <a-button type="primary" class="warm-primary-btn" :loading="createLoading" @click="handleCreatePromoCode">
            <template #icon><UserAddOutlined /></template>
            {{ createLoading ? "创建中..." : "创建推广码" }}
          </a-button>
          <a-button class="warm-secondary-btn" @click="handleReset">
            <template #icon><UndoOutlined /></template>
            重置
          </a-button>
        </div>
        </div>
      </div>

      <div class="warm-card warm-table-card promo-table-card motion-fade-up motion-card-lift" style="--motion-delay: 180ms">
        <div class="section-title">推广码列表</div>
        <a-table
          class="promo-table"
          :columns="promoColumns"
          :data-source="promoCodes"
          :loading="loading"
          row-key="id"
          :pagination="false"
          :scroll="{ x: 920 }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'status'">
              <a-tag class="warm-tag" :color="record.status === 'enabled' ? 'green' : 'default'">
                {{ record.status === "enabled" ? "启用中" : "已停用" }}
              </a-tag>
            </template>
            <template v-else-if="column.dataIndex === 'created_at'">
              {{ formatTime(record.created_at) }}
            </template>
            <template v-else-if="column.dataIndex === 'platform_name'">
              <div v-if="editingPromoId === record.id" class="promo-edit-inline">
                <a-input
                  v-model:value="editPlatformName"
                  size="small"
                  :maxlength="50"
                  @press-enter="saveEditPromo(record)"
                />
              </div>
              <span v-else>{{ record.platform_name }}</span>
            </template>
            <template v-else-if="column.key === 'actions'">
              <div class="promo-action-group">
                <template v-if="editingPromoId === record.id">
                  <a-button
                    type="link"
                    class="promo-link-btn"
                    :loading="saveEditingLoading"
                    @click="saveEditPromo(record)"
                  >
                    保存
                  </a-button>
                  <a-button type="link" class="promo-link-btn" @click="cancelEditPromo">
                    取消
                  </a-button>
                </template>
                <template v-else>
                  <a-button type="link" class="promo-link-btn" @click="startEditPromo(record)">
                    编辑平台
                  </a-button>
                  <a-button type="link" class="promo-link-btn" @click="copyPromoCode(record.code)">
                    <template #icon><CopyOutlined /></template>
                    复制
                  </a-button>
                </template>
              </div>
            </template>
          </template>
        </a-table>
      </div>

      <div class="warm-card warm-table-card promo-table-card motion-fade-up motion-card-lift" style="--motion-delay: 300ms">
        <div class="promo-filter-bar">
          <a-input
            v-model:value="referralFilters.keyword"
            allow-clear
            placeholder="按名称或邮箱筛选"
            class="promo-filter-input"
            @press-enter="handleSearch"
          />
          <a-select
            v-model:value="referralFilters.platformName"
            allow-clear
            placeholder="全部推广平台"
            class="promo-filter-select"
          >
            <a-select-option
              v-for="item in promoCodes"
              :key="item.id"
              :value="item.platform_name"
            >
              {{ item.platform_name }}
            </a-select-option>
          </a-select>
          <a-range-picker v-model:value="referralFilters.dateRange" class="promo-filter-date" />
          <a-button type="primary" class="warm-primary-btn" @click="handleSearch">查询</a-button>
          <a-button class="warm-secondary-btn" @click="handleResetFilters">
            <template #icon><UndoOutlined /></template>
            重置
          </a-button>
        </div>
        <div class="section-title">推广用户列表</div>
        <a-table
          class="promo-table"
          :columns="referralColumns"
          :data-source="referrals"
          :loading="loading"
          row-key="user_id"
          :pagination="false"
          table-layout="fixed"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'user'">
              <div class="promo-user-cell">
                <span class="promo-user-name">{{ record.username || "-" }}</span>
                <span v-if="record.email_masked" class="promo-user-email">{{ record.email_masked }}</span>
              </div>
            </template>
            <template v-else-if="column.dataIndex === 'registered_at'">
              {{ formatTime(record.registered_at) }}
            </template>
          </template>
        </a-table>
      </div>

      <div class="warm-card warm-table-card promo-table-card motion-fade-up motion-card-lift" style="--motion-delay: 360ms">
        <div class="section-title">推广用户积分记录</div>
        <a-table
          class="promo-table"
          :columns="activityColumns"
          :data-source="activities"
          :loading="loading"
          row-key="occurred_at"
          :pagination="false"
          table-layout="fixed"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'user'">
              <div class="promo-user-cell">
                <span class="promo-user-name">{{ record.username || "-" }}</span>
                <span v-if="record.email_masked" class="promo-user-email">{{ record.email_masked }}</span>
              </div>
            </template>
            <template v-else-if="column.dataIndex === 'activity_type'">
              {{ record.activity_type === "purchase" ? "购买订单" : "兑换码兑换" }}
            </template>
            <template v-else-if="column.dataIndex === 'amount_yuan'">
              {{ record.amount_yuan != null ? `¥${record.amount_yuan.toFixed(2)}` : "-" }}
            </template>
            <template v-else-if="column.dataIndex === 'activity_ref'">
              {{ record.order_no || record.redeem_key || "-" }}
            </template>
            <template v-else-if="column.dataIndex === 'occurred_at'">
              {{ formatTime(record.occurred_at) }}
            </template>
          </template>
        </a-table>
      </div>
    </template>
  </div>
</template>

<style scoped lang="scss">
.promo-page {
  display: grid;
  gap: 20px;
}

.promo-empty {
  padding: 24px;
  color: var(--theme-text-secondary);
}

.promo-top-row {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr);
  gap: 16px;
  align-items: stretch;
}

.promo-stat-card {
  display: grid;
  gap: 10px;
  padding: 20px 22px;
  align-content: center;

  span {
    color: var(--theme-text-secondary);
    font-size: 13px;
  }

  strong {
    color: var(--theme-title);
    font-size: 30px;
    line-height: 1;
  }

  em {
    color: var(--theme-text-secondary);
    font-size: 12px;
    font-style: normal;
  }
}

.promo-create-card {
  display: grid;
  gap: 16px;
  padding: 22px 24px;
}

.promo-create-title,
.section-title {
  color: var(--theme-title);
  font-size: 18px;
  font-weight: 700;
}

.promo-create-desc {
  margin-top: 6px;
  color: var(--theme-text-secondary);
  font-size: 13px;
}

.promo-create-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 12px;
  align-items: center;
}

.promo-filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.promo-filter-input {
  width: 220px;
}

.promo-filter-select {
  width: 180px;
}

.promo-filter-date {
  width: 280px;
}

.section-title {
  margin-bottom: 16px;
}

.promo-table-card {
  padding: 22px 24px 24px;
}

.promo-user-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.promo-user-name {
  color: var(--theme-title);
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.promo-user-email {
  color: var(--theme-text-secondary);
  font-size: 12px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.promo-table {
  :deep(.ant-table-title) {
    padding-inline: 0;
  }

  :deep(.ant-table-container) {
    overflow: hidden;
    border-radius: 16px;
  }

  :deep(.ant-table-thead > tr > th:first-child),
  :deep(.ant-table-tbody > tr > td:first-child) {
    padding-left: 24px;
  }

  :deep(.ant-table-thead > tr > th:last-child),
  :deep(.ant-table-tbody > tr > td:last-child) {
    padding-right: 24px;
  }
}

.promo-link-btn {
  padding-inline: 0;
}

.promo-edit-inline {
  min-width: 160px;
}

.promo-action-group {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 960px) {
  .promo-top-row {
    grid-template-columns: 1fr;
  }

  .promo-create-form {
    grid-template-columns: 1fr;
  }

  .promo-filter-input,
  .promo-filter-select,
  .promo-filter-date {
    width: 100%;
  }

  .promo-create-card,
  .promo-table-card {
    padding: 18px 16px;
  }

  .promo-table {
    :deep(.ant-table-thead > tr > th:first-child),
    :deep(.ant-table-tbody > tr > td:first-child) {
      padding-left: 16px;
    }

    :deep(.ant-table-thead > tr > th:last-child),
    :deep(.ant-table-tbody > tr > td:last-child) {
      padding-right: 16px;
    }
  }
}
</style>
