<template>
  <div class="logs-page">
    <el-tabs v-model="activeTab" class="logs-tabs">
      <el-tab-pane label="访问日志" name="access">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>访问日志</span>
            </div>
          </template>
          
          <el-form inline class="search-form">
            <el-form-item label="用户ID">
              <el-input v-model="searchForm.user_id" placeholder="用户ID" clearable @keyup.enter="loadAccessLogs" />
            </el-form-item>
            <el-form-item label="页面">
              <el-input v-model="searchForm.page" placeholder="页面路径" clearable @keyup.enter="loadAccessLogs" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadAccessLogs">搜索</el-button>
            </el-form-item>
          </el-form>
          
          <el-table :data="accessLogs" stripe v-loading="loading">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="user_id" label="用户ID" width="120" />
            <el-table-column prop="page" label="页面" min-width="180" />
            <el-table-column prop="action" label="操作" width="100" />
            <el-table-column prop="target_id" label="目标ID" width="120" />
            <el-table-column prop="ip" label="IP地址" width="130" />
            <el-table-column label="访问时间" width="160">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
          
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="pagination.page"
              v-model:page-size="pagination.page_size"
              :total="pagination.total"
              :page-sizes="[20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @size-change="loadAccessLogs"
              @current-change="loadAccessLogs"
            />
          </div>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="运营日志" name="operation">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>运营日志</span>
            </div>
          </template>
          
          <el-table :data="operationLogs" stripe v-loading="loading2">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="admin_name" label="管理员" width="120" />
            <el-table-column label="模块" width="120">
              <template #default="{ row }">
                {{ row.module }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ row.action }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作对象" min-width="150">
              <template #default="{ row }">
                <div>{{ row.target_name }}</div>
                <div class="text-small">ID: {{ row.target_id }}</div>
              </template>
            </el-table-column>
            <el-table-column prop="remark" label="备注" width="150" show-overflow-tooltip />
            <el-table-column prop="ip" label="IP地址" width="130" />
            <el-table-column label="操作时间" width="160">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
          
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="pagination2.page"
              v-model:page-size="pagination2.page_size"
              :total="pagination2.total"
              :page-sizes="[20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @size-change="loadOperationLogs"
              @current-change="loadOperationLogs"
            />
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getAccessLogs, getOperationLogs } from '../api'

const activeTab = ref('access')
const loading = ref(false)
const loading2 = ref(false)

const searchForm = reactive({
  user_id: '',
  page: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const pagination2 = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const accessLogs = ref([])
const operationLogs = ref([])

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const loadAccessLogs = async () => {
  loading.value = true
  try {
    const data = await getAccessLogs({
      page: pagination.page,
      page_size: pagination.page_size,
      user_id: searchForm.user_id || undefined,
      page_path: searchForm.page || undefined
    })
    accessLogs.value = data.list || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('加载访问日志失败:', error)
  } finally {
    loading.value = false
  }
}

const loadOperationLogs = async () => {
  loading2.value = true
  try {
    const data = await getOperationLogs({
      page: pagination2.page,
      page_size: pagination2.page_size
    })
    operationLogs.value = data.list || []
    pagination2.total = data.total || 0
  } catch (error) {
    console.error('加载运营日志失败:', error)
  } finally {
    loading2.value = false
  }
}

onMounted(() => {
  loadAccessLogs()
})
</script>

<style scoped>
.logs-page {
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

.text-small {
  font-size: 12px;
  color: #909399;
}
</style>
