<template>
  <div class="orders-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>订单管理</span>
        </div>
      </template>
      
      <!-- 筛选栏 -->
      <el-form inline class="search-form">
        <el-form-item label="订单状态">
          <el-select v-model="searchForm.status" placeholder="选择状态" clearable @change="loadOrders">
            <el-option label="全部" value="" />
            <el-option label="待付款" value="pending" />
            <el-option label="待发货" value="paid" />
            <el-option label="待收货" value="shipped" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="订单号">
          <el-input v-model="searchForm.order_id" placeholder="订单号" clearable @keyup.enter="loadOrders" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadOrders">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
      
      <!-- 订单表格 -->
      <el-table :data="orders" stripe v-loading="loading">
        <el-table-column prop="order_id" label="订单号" width="180" />
        <el-table-column label="商品信息" min-width="200">
          <template #default="{ row }">
            <div class="product-info">
              <p class="product-name">{{ row.product_name }}</p>
              <p class="product-spec">{{ row.sku_spec }}</p>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="买手" width="120">
          <template #default="{ row }">
            {{ row.buyer_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="订单金额" width="120">
          <template #default="{ row }">
            <span class="price">¥{{ row.total_amount?.toLocaleString() }}</span>
          </template>
        </el-table-column>
        <el-table-column label="订单状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="下单时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="viewDetail(row)">详情</el-button>
            <el-dropdown v-if="row.status === 'paid'" @command="(cmd) => handleAction(row, cmd)">
              <el-button type="warning" size="small" link>发货</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="shipped">确认发货</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-dropdown v-if="row.status === 'shipped'" @command="(cmd) => handleAction(row, cmd)">
              <el-button type="success" size="small" link>完成</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="completed">确认完成</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="loadOrders"
          @current-change="loadOrders"
        />
      </div>
    </el-card>
    
    <!-- 订单详情抽屉 -->
    <el-drawer v-model="detailVisible" title="订单详情" size="600px">
      <div v-if="currentOrder" class="order-detail">
        <el-descriptions title="订单信息" :column="2" border>
          <el-descriptions-item label="订单号">{{ currentOrder.order_id }}</el-descriptions-item>
          <el-descriptions-item label="订单状态">
            <el-tag :type="getStatusType(currentOrder.status)">{{ getStatusText(currentOrder.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="下单时间">{{ formatDate(currentOrder.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="支付时间">{{ formatDate(currentOrder.paid_at) }}</el-descriptions-item>
        </el-descriptions>
        
        <el-descriptions title="商品信息" :column="2" border style="margin-top: 20px;">
          <el-descriptions-item label="商品名称" :span="2">{{ currentOrder.product_name }}</el-descriptions-item>
          <el-descriptions-item label="规格">{{ currentOrder.sku_spec }}</el-descriptions-item>
          <el-descriptions-item label="数量">{{ currentOrder.quantity }}</el-descriptions-item>
          <el-descriptions-item label="原价">{{ currentOrder.original_price }} {{ currentOrder.original_currency }}</el-descriptions-item>
          <el-descriptions-item label="人民币价格">¥{{ currentOrder.cny_price?.toLocaleString() }}</el-descriptions-item>
        </el-descriptions>
        
        <el-descriptions title="费用明细" :column="2" border style="margin-top: 20px;">
          <el-descriptions-item label="商品价格">¥{{ (currentOrder.cny_price * currentOrder.quantity)?.toLocaleString() }}</el-descriptions-item>
          <el-descriptions-item label="服务费">{{ currentOrder.fee_rate }}% (¥{{ currentOrder.fee_amount?.toLocaleString() }})</el-descriptions-item>
          <el-descriptions-item label="运费">¥{{ currentOrder.shipping_fee?.toLocaleString() }}</el-descriptions-item>
          <el-descriptions-item label="订单总额">
            <span class="price">¥{{ currentOrder.total_amount?.toLocaleString() }}</span>
          </el-descriptions-item>
        </el-descriptions>
        
        <el-descriptions title="买手信息" :column="2" border style="margin-top: 20px;">
          <el-descriptions-item label="买手">{{ currentOrder.buyer_name }}</el-descriptions-item>
          <el-descriptions-item label="采购地">{{ currentOrder.country }} - {{ currentOrder.store }}</el-descriptions-item>
        </el-descriptions>
        
        <el-descriptions title="收货信息" :column="2" border style="margin-top: 20px;">
          <el-descriptions-item label="收货人">{{ currentOrder.receiver_name }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ currentOrder.receiver_phone }}</el-descriptions-item>
          <el-descriptions-item label="收货地址" :span="2">{{ currentOrder.receiver_address }}</el-descriptions-item>
        </el-descriptions>
        
        <el-descriptions v-if="currentOrder.tracking_no" title="物流信息" :column="2" border style="margin-top: 20px;">
          <el-descriptions-item label="快递公司">{{ currentOrder.tracking_company }}</el-descriptions-item>
          <el-descriptions-item label="运单号">{{ currentOrder.tracking_no }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getOrders, updateOrderStatus } from '../api'

const loading = ref(false)
const detailVisible = ref(false)
const currentOrder = ref(null)

const searchForm = reactive({
  status: '',
  order_id: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const orders = ref([])

const statusMap = {
  pending: { text: '待付款', type: 'info' },
  paid: { text: '待发货', type: 'warning' },
  shipped: { text: '待收货', type: 'primary' },
  completed: { text: '已完成', type: 'success' },
  cancelled: { text: '已取消', type: 'danger' },
  refunded: { text: '已退款', type: 'info' }
}

const getStatusText = (status) => statusMap[status]?.text || status
const getStatusType = (status) => statusMap[status]?.type || 'info'

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const loadOrders = async () => {
  loading.value = true
  try {
    const data = await getOrders({
      page: pagination.page,
      page_size: pagination.page_size,
      status: searchForm.status || undefined,
      order_id: searchForm.order_id || undefined
    })
    orders.value = data.list || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('加载订单列表失败:', error)
  } finally {
    loading.value = false
  }
}

const resetSearch = () => {
  searchForm.status = ''
  searchForm.order_id = ''
  pagination.page = 1
  loadOrders()
}

const viewDetail = (row) => {
  currentOrder.value = row
  detailVisible.value = true
}

const handleAction = async (row, action) => {
  try {
    await updateOrderStatus(row.order_id, action)
    ElMessage.success('操作成功')
    loadOrders()
    if (detailVisible.value) {
      currentOrder.value = { ...currentOrder.value, status: action }
    }
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  loadOrders()
})
</script>

<style scoped>
.orders-page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-form {
  margin-bottom: 20px;
}

.pagination-wrap {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.product-info {
  line-height: 1.4;
}

.product-name {
  font-weight: 500;
  color: #303133;
}

.product-spec {
  font-size: 12px;
  color: #909399;
}

.price {
  font-weight: bold;
  color: #F56C6C;
}

.order-detail {
  padding: 0 10px;
}
</style>
