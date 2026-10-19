<template>
  <div class="stores-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>门店管理</span>
        </div>
      </template>
      
      <el-table :data="stores" stripe v-loading="loading">
        <el-table-column prop="store_id" label="门店ID" width="100" />
        <el-table-column prop="name" label="门店名称" min-width="180" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            {{ getTypeName(row.type) }}
          </template>
        </el-table-column>
        <el-table-column label="国家/地区" width="100">
          <template #default="{ row }">
            {{ row.country }}
          </template>
        </el-table-column>
        <el-table-column prop="city" label="城市" width="100" />
        <el-table-column prop="address" label="地址" min-width="250" show-overflow-tooltip />
        <el-table-column label="评分" width="100">
          <template #default="{ row }">
            <el-rate v-model="row.rating" disabled size="small" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getStores } from '../api'

const loading = ref(false)
const stores = ref([])

const typeMap = {
  mall: '商场',
  street: '专卖店街',
  dutyfree: '免税店'
}

const getTypeName = (type) => typeMap[type] || type

const loadStores = async () => {
  loading.value = true
  try {
    const data = await getStores({ page: 1, page_size: 100 })
    stores.value = data.list || []
  } catch (error) {
    console.error('加载门店列表失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStores()
})
</script>

<style scoped>
.stores-page {
  padding: 0;
}
</style>
