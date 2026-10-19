<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon user-icon">
            <el-icon :size="32"><ele-User /></el-icon>
          </div>
          <div class="stat-info">
            <p class="stat-label">用户总数</p>
            <p class="stat-value">{{ stats.user?.total || 0 }}</p>
            <p class="stat-tag">今日新增 {{ stats.user?.today_new || 0 }}</p>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon order-icon">
            <el-icon :size="32"><ele-ShoppingCart /></el-icon>
          </div>
          <div class="stat-info">
            <p class="stat-label">订单总数</p>
            <p class="stat-value">{{ stats.order?.total || 0 }}</p>
            <p class="stat-tag">今日订单 {{ stats.order?.today || 0 }}</p>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon sales-icon">
            <el-icon :size="32"><ele-Coin /></el-icon>
          </div>
          <div class="stat-info">
            <p class="stat-label">总销售额</p>
            <p class="stat-value">¥{{ formatNumber(stats.order?.total_sales || 0) }}</p>
            <p class="stat-tag">今日 ¥{{ formatNumber(stats.order?.today_sales || 0) }}</p>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-icon traffic-icon">
            <el-icon :size="32"><ele-View /></el-icon>
          </div>
          <div class="stat-info">
            <p class="stat-label">今日访问</p>
            <p class="stat-value">{{ stats.traffic?.today_pv || 0 }} PV</p>
            <p class="stat-tag">{{ stats.traffic?.today_uv || 0 }} UV</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="16">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>订单趋势</span>
              <el-radio-group v-model="orderDays" size="small" @change="loadOrderTrend">
                <el-radio-button :value="7">近7天</el-radio-button>
                <el-radio-button :value="15">近15天</el-radio-button>
                <el-radio-button :value="30">近30天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="orderChartRef" class="chart"></div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="chart-card">
          <template #header>
            <span>数据概览</span>
          </template>
          <div class="overview-list">
            <div class="overview-item">
              <span class="label">VIP用户</span>
              <span class="value">{{ stats.user?.vip || 0 }}</span>
            </div>
            <div class="overview-item">
              <span class="label">买手数量</span>
              <span class="value">{{ stats.user?.buyer || 0 }}</span>
            </div>
            <div class="overview-item">
              <span class="label">商品总数</span>
              <span class="value">{{ stats.product?.total || 0 }}</span>
            </div>
            <div class="overview-item">
              <span class="label">品牌数量</span>
              <span class="value">{{ stats.product?.brands || 0 }}</span>
            </div>
            <div class="overview-item">
              <span class="label">优惠券数</span>
              <span class="value">{{ stats.other?.coupons || 0 }}</span>
            </div>
            <div class="overview-item">
              <span class="label">门店数量</span>
              <span class="value">{{ stats.other?.stores || 0 }}</span>
            </div>
            <div class="overview-item">
              <span class="label">待付款订单</span>
              <span class="value warning">{{ stats.order?.total - stats.order?.paid - stats.order?.completed }}</span>
            </div>
            <div class="overview-item">
              <span class="label">已完成订单</span>
              <span class="value success">{{ stats.order?.completed || 0 }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 流量趋势 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="24">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>流量趋势</span>
              <el-radio-group v-model="trafficDays" size="small" @change="loadTrafficTrend">
                <el-radio-button :value="7">近7天</el-radio-button>
                <el-radio-button :value="15">近15天</el-radio-button>
                <el-radio-button :value="30">近30天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="trafficChartRef" class="chart traffic-chart"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getDashboardStats, getOrderTrend, getTrafficTrend } from '../api'

const stats = reactive({
  user: {},
  order: {},
  product: {},
  traffic: {},
  other: {}
})

const orderDays = ref(7)
const trafficDays = ref(7)

const orderChartRef = ref(null)
const trafficChartRef = ref(null)
let orderChart = null
let trafficChart = null

const formatNumber = (num) => {
  return String(num).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

const loadStats = async () => {
  try {
    const data = await getDashboardStats()
    Object.assign(stats, data)
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

const loadOrderTrend = async () => {
  if (!orderChart) return
  try {
    const data = await getOrderTrend(orderDays.value)
    const dates = data.map(item => item.date)
    const orders = data.map(item => item.orders)
    const sales = data.map(item => item.sales)
    
    orderChart.setOption({
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      legend: { data: ['订单数', '销售额'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: dates },
      yAxis: [
        { type: 'value', name: '订单数', position: 'left' },
        { type: 'value', name: '销售额', position: 'right', axisLabel: { formatter: '¥{value}' } }
      ],
      series: [
        { name: '订单数', type: 'bar', data: orders, itemStyle: { color: '#409EFF' } },
        { name: '销售额', type: 'line', yAxisIndex: 1, data: sales, itemStyle: { color: '#67C23A' }, smooth: true }
      ]
    })
  } catch (error) {
    console.error('加载订单趋势失败:', error)
  }
}

const loadTrafficTrend = async () => {
  if (!trafficChart) return
  try {
    const data = await getTrafficTrend(trafficDays.value)
    const dates = data.map(item => item.date)
    const pv = data.map(item => item.pv)
    const uv = data.map(item => item.uv)
    
    trafficChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['PV', 'UV'] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: dates },
      yAxis: { type: 'value' },
      series: [
        { name: 'PV', type: 'line', data: pv, itemStyle: { color: '#409EFF' }, smooth: true, areaStyle: { color: 'rgba(64, 158, 255, 0.1)' } },
        { name: 'UV', type: 'line', data: uv, itemStyle: { color: '#E6A23C' }, smooth: true, areaStyle: { color: 'rgba(230, 162, 60, 0.1)' } }
      ]
    })
  } catch (error) {
    console.error('加载流量趋势失败:', error)
  }
}

const initCharts = () => {
  nextTick(() => {
    if (orderChartRef.value) {
      orderChart = echarts.init(orderChartRef.value)
      loadOrderTrend()
    }
    if (trafficChartRef.value) {
      trafficChart = echarts.init(trafficChartRef.value)
      loadTrafficTrend()
    }
  })
}

onMounted(() => {
  loadStats()
  initCharts()
  
  window.addEventListener('resize', () => {
    orderChart?.resize()
    trafficChart?.resize()
  })
})
</script>

<style scoped>
.dashboard {
  padding: 0;
}

.stat-row {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.user-icon { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.order-icon { background: linear-gradient(135deg, #409EFF 0%, #66b1ff 100%); }
.sales-icon { background: linear-gradient(135deg, #67C23A 0%, #85ce61 100%); }
.traffic-icon { background: linear-gradient(135deg, #E6A23C 0%, #ebb563 100%); }

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.stat-tag {
  font-size: 12px;
  color: #909399;
}

.chart-row {
  margin-bottom: 20px;
}

.chart-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart {
  height: 300px;
}

.traffic-chart {
  height: 250px;
}

.overview-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.overview-item {
  display: flex;
  justify-content: space-between;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.overview-item .label {
  color: #909399;
  font-size: 14px;
}

.overview-item .value {
  font-weight: bold;
  font-size: 16px;
  color: #303133;
}

.overview-item .value.warning {
  color: #E6A23C;
}

.overview-item .value.success {
  color: #67C23A;
}
</style>
