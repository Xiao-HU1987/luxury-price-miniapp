<template>
  <div class="demands-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>需求管理</span>
        </div>
      </template>
      
      <el-table :data="demands" stripe v-loading="loading">
        <el-table-column prop="demand_id" label="需求ID" width="140" />
        <el-table-column prop="product_name" label="商品名称" min-width="180" />
        <el-table-column prop="brand_id" label="品牌" width="100" />
        <el-table-column label="目标国家" width="100">
          <template #default="{ row }">
            {{ getCountryName(row.country) }}
          </template>
        </el-table-column>
        <el-table-column label="预算" width="120">
          <template #default="{ row }">
            ¥{{ row.budget?.toLocaleString() }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="截止日期" width="120">
          <template #default="{ row }">
            {{ row.deadline }}
          </template>
        </el-table-column>
        <el-table-column label="发布时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getDemands } from '../api'

const loading = ref(false)
const demands = ref([])

const countryMap = {
  JP: '日本', FR: '法国', HK: '香港', KR: '韩国'
}

const statusMap = {
  bidding: { text: '招标中', type: 'primary' },
  matched: { text: '已匹配', type: 'success' },
  completed: { text: '已完成', type: 'info' }
}

const getCountryName = (code) => countryMap[code] || code
const getStatusText = (status) => statusMap[status]?.text || status
const getStatusType = (status) => statusMap[status]?.type || 'info'

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const loadDemands = async () => {
  loading.value = true
  try {
    const data = await getDemands({ page: 1, page_size: 100 })
    demands.value = data.list || []
  } catch (error) {
    console.error('加载需求列表失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDemands()
})
</script>

<style scoped>
.demands-page {
  padding: 0;
}
</style>
