<template>
  <div class="trino-page">
    <el-card class="hero-card" shadow="hover">
      <div class="hero-grid">
        <div>
          <p class="eyebrow">Trino 数据中心</p>
          <h1>以 Trino 作为读数据源的后台入口</h1>
          <p class="subtitle">
            这里展示 Trino 连通性、汇率快照，以及买手、门店、优惠券、订单的读数据。
          </p>
        </div>
        <div class="status-panel" :class="healthClass">
          <div class="status-dot"></div>
          <div>
            <p class="status-label">当前状态</p>
            <p class="status-value">{{ healthStatusText }}</p>
            <p class="status-meta">{{ healthMeta }}</p>
          </div>
        </div>
      </div>
    </el-card>

    <el-row :gutter="20" class="summary-row">
      <el-col :span="6">
        <el-card class="mini-card" shadow="hover">
          <div class="mini-label">Trino 主机</div>
          <div class="mini-value">{{ health.host || 'localhost' }}:{{ health.port || 8080 }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-card" shadow="hover">
          <div class="mini-label">Catalog</div>
          <div class="mini-value">{{ health.catalog || 'hive' }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-card" shadow="hover">
          <div class="mini-label">Schema</div>
          <div class="mini-value">{{ health.schema || 'default' }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="mini-card" shadow="hover">
          <div class="mini-label">汇率基准</div>
          <div class="mini-value">{{ summary.exchange_rates?.base || 'CNY' }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>Trino 数据浏览</span>
          <el-button type="primary" plain @click="reloadAll" :loading="loading">
            刷新
          </el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="总览" name="overview">
          <el-row :gutter="16" class="overview-grid">
            <el-col :span="8">
              <el-card shadow="never" class="overview-card">
                <div class="overview-title">买手</div>
                <div class="overview-count">{{ buyerData.total || 0 }}</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="never" class="overview-card">
                <div class="overview-title">门店</div>
                <div class="overview-count">{{ storeData.total || 0 }}</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="never" class="overview-card">
                <div class="overview-title">优惠券</div>
                <div class="overview-count">{{ couponData.total || 0 }}</div>
              </el-card>
            </el-col>
          </el-row>

          <el-row :gutter="16" class="overview-grid second">
            <el-col :span="8">
              <el-card shadow="never" class="overview-card">
                <div class="overview-title">订单</div>
                <div class="overview-count">{{ orderData.total || 0 }}</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="never" class="overview-card">
                <div class="overview-title">汇率更新时间</div>
                <div class="overview-count small">{{ summary.exchange_rates?.update_time || '-' }}</div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="never" class="overview-card">
                <div class="overview-title">Trino 连接</div>
                <div class="overview-count small">{{ health.status || 'unknown' }}</div>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <el-tab-pane label="买手" name="buyers">
          <el-table :data="buyerData.list || []" v-loading="loadingBuyers" stripe>
            <el-table-column prop="buyer_id" label="买手ID" width="120" />
            <el-table-column prop="name" label="名称" width="140" />
            <el-table-column prop="country" label="国家" width="90" />
            <el-table-column prop="city" label="城市" width="120" />
            <el-table-column prop="rating" label="评分" width="80" />
            <el-table-column prop="orders" label="订单数" width="90" />
            <el-table-column prop="fee_rate" label="费率%" width="90" />
            <el-table-column prop="delivery_days" label="交货天数" width="100" />
            <el-table-column prop="intro" label="简介" min-width="240" show-overflow-tooltip />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="门店" name="stores">
          <el-table :data="storeData.list || []" v-loading="loadingStores" stripe>
            <el-table-column prop="store_id" label="门店ID" width="120" />
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column prop="type" label="类型" width="100" />
            <el-table-column prop="country" label="国家" width="90" />
            <el-table-column prop="city" label="城市" width="120" />
            <el-table-column prop="rating" label="评分" width="80" />
            <el-table-column prop="address" label="地址" min-width="240" show-overflow-tooltip />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="优惠券" name="coupons">
          <el-table :data="couponData.list || []" v-loading="loadingCoupons" stripe>
            <el-table-column prop="coupon_id" label="优惠券ID" width="120" />
            <el-table-column prop="title" label="标题" min-width="200" />
            <el-table-column prop="type" label="类型" width="100" />
            <el-table-column prop="discount" label="折扣/减免" width="100" />
            <el-table-column prop="country" label="国家" width="90" />
            <el-table-column prop="store_name" label="店铺" min-width="160" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column prop="expire_date" label="有效期" width="120" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="订单" name="orders">
          <el-table :data="orderData.list || []" v-loading="loadingOrders" stripe>
            <el-table-column prop="order_id" label="订单号" width="180" />
            <el-table-column prop="product_name" label="商品" min-width="180" show-overflow-tooltip />
            <el-table-column prop="buyer_name" label="买手" width="120" />
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column prop="country" label="国家" width="90" />
            <el-table-column prop="total_amount" label="总金额" width="100" />
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import {
  getTrinoHealth,
  getTrinoSummary,
  getTrinoBuyers,
  getTrinoStores,
  getTrinoCoupons,
  getTrinoOrders,
} from '../api'

const activeTab = ref('overview')
const loading = ref(false)
const loadingBuyers = ref(false)
const loadingStores = ref(false)
const loadingCoupons = ref(false)
const loadingOrders = ref(false)

const health = reactive({})
const summary = reactive({ exchange_rates: {} })
const buyerData = reactive({ list: [], total: 0 })
const storeData = reactive({ list: [], total: 0 })
const couponData = reactive({ list: [], total: 0 })
const orderData = reactive({ list: [], total: 0 })

const healthStatusText = computed(() => {
  if (!health.enabled) return '已禁用'
  if (health.status === 'ok') return '连通正常'
  if (health.status === 'error') return '连接异常'
  return '未知'
})

const healthClass = computed(() => {
  if (!health.enabled) return 'status-disabled'
  if (health.status === 'ok') return 'status-ok'
  return 'status-error'
})

const healthMeta = computed(() => {
  return `${health.host || 'localhost'}:${health.port || 8080}`
})

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const loadHealth = async () => {
  const data = await getTrinoHealth()
  Object.assign(health, data)
}

const loadSummary = async () => {
  const data = await getTrinoSummary()
  if (data) {
    Object.assign(summary, data)
    if (data.buyers) Object.assign(buyerData, data.buyers)
    if (data.stores) Object.assign(storeData, data.stores)
    if (data.coupons) Object.assign(couponData, data.coupons)
    if (data.orders) Object.assign(orderData, data.orders)
  }
}

const loadBuyers = async () => {
  loadingBuyers.value = true
  try {
    const data = await getTrinoBuyers({ page: 1, page_size: 20 })
    Object.assign(buyerData, data)
  } finally {
    loadingBuyers.value = false
  }
}

const loadStores = async () => {
  loadingStores.value = true
  try {
    const data = await getTrinoStores({ page: 1, page_size: 20 })
    Object.assign(storeData, data)
  } finally {
    loadingStores.value = false
  }
}

const loadCoupons = async () => {
  loadingCoupons.value = true
  try {
    const data = await getTrinoCoupons({ page: 1, page_size: 20 })
    Object.assign(couponData, data)
  } finally {
    loadingCoupons.value = false
  }
}

const loadOrders = async () => {
  loadingOrders.value = true
  try {
    const data = await getTrinoOrders({ page: 1, page_size: 20 })
    Object.assign(orderData, data)
  } finally {
    loadingOrders.value = false
  }
}

const reloadAll = async () => {
  loading.value = true
  try {
    await Promise.all([loadHealth(), loadSummary(), loadBuyers(), loadStores(), loadCoupons(), loadOrders()])
  } finally {
    loading.value = false
  }
}

const handleTabChange = (tabName) => {
  if (tabName === 'buyers' && !buyerData.list.length) loadBuyers()
  if (tabName === 'stores' && !storeData.list.length) loadStores()
  if (tabName === 'coupons' && !couponData.list.length) loadCoupons()
  if (tabName === 'orders' && !orderData.list.length) loadOrders()
}

onMounted(() => {
  reloadAll()
})
</script>

<style scoped>
.trino-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card {
  background: linear-gradient(135deg, #101828 0%, #1d4ed8 55%, #0f766e 100%);
  color: #fff;
}

.hero-grid {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: center;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 12px;
  opacity: 0.78;
  margin-bottom: 8px;
}

.hero-grid h1 {
  margin: 0;
  font-size: 28px;
  line-height: 1.2;
}

.subtitle {
  margin: 12px 0 0;
  max-width: 640px;
  color: rgba(255, 255, 255, 0.82);
}

.status-panel {
  min-width: 240px;
  border-radius: 16px;
  padding: 18px 20px;
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  gap: 14px;
  align-items: center;
  backdrop-filter: blur(8px);
}

.status-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #67c23a;
  box-shadow: 0 0 0 8px rgba(103, 194, 58, 0.15);
}

.status-disabled .status-dot {
  background: #909399;
  box-shadow: 0 0 0 8px rgba(144, 147, 153, 0.12);
}

.status-error .status-dot {
  background: #f56c6c;
  box-shadow: 0 0 0 8px rgba(245, 108, 108, 0.12);
}

.status-label {
  font-size: 12px;
  opacity: 0.72;
  margin: 0;
}

.status-value {
  font-size: 20px;
  font-weight: 700;
  margin: 4px 0;
}

.status-meta {
  font-size: 12px;
  opacity: 0.72;
  margin: 0;
}

.summary-row {
  margin-top: 0;
}

.mini-card {
  min-height: 92px;
}

.mini-label {
  font-size: 12px;
  color: #6b7280;
}

.mini-value {
  margin-top: 10px;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  word-break: break-all;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.overview-grid {
  margin-bottom: 16px;
}

.overview-card {
  min-height: 110px;
}

.overview-title {
  color: #6b7280;
  font-size: 13px;
}

.overview-count {
  margin-top: 10px;
  font-size: 28px;
  font-weight: 800;
  color: #111827;
}

.overview-count.small {
  font-size: 18px;
  word-break: break-all;
}
</style>
