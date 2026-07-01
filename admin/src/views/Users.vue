<template>
  <div class="users-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
        </div>
      </template>
      
      <!-- 搜索栏 -->
      <el-form inline class="search-form">
        <el-form-item label="用户ID">
          <el-input v-model="searchForm.user_id" placeholder="用户ID" clearable @keyup.enter="loadUsers" />
        </el-form-item>
        <el-form-item label="用户类型">
          <el-select v-model="searchForm.role" placeholder="选择类型" clearable>
            <el-option label="全部" value="" />
            <el-option label="VIP用户" value="vip" />
            <el-option label="买手用户" value="buyer" />
            <el-option label="普通用户" value="normal" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadUsers">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
      
      <!-- 用户表格 -->
      <el-table :data="users" stripe v-loading="loading">
        <el-table-column prop="user_id" label="用户ID" width="180" />
        <el-table-column label="用户信息" width="180">
          <template #default="{ row }">
            <div class="user-info">
              <el-avatar :size="40" :src="row.avatar">
                <el-icon><ele-UserFilled /></el-icon>
              </el-avatar>
              <span>{{ row.nickname || '未设置昵称' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="phone" label="手机号" width="130" />
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.is_admin" type="danger" size="small">管理员</el-tag>
            <el-tag v-else-if="row.is_vip" type="warning" size="small">VIP</el-tag>
            <el-tag v-if="row.is_buyer" type="success" size="small">买手</el-tag>
            <span v-if="!row.is_vip && !row.is_buyer && !row.is_admin" class="text-gray">普通用户</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="注册时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="viewDetail(row)">详情</el-button>
            <el-button type="warning" size="small" link @click="openEditDialog(row)">编辑</el-button>
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
          @size-change="loadUsers"
          @current-change="loadUsers"
        />
      </div>
    </el-card>
    
    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" title="编辑用户" width="500px">
      <el-form ref="formRef" :model="form" label-width="100px">
        <el-form-item label="用户ID">
          <el-input v-model="form.user_id" disabled />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="form.nickname" placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item label="角色">
          <el-checkbox v-model="form.is_vip">VIP用户</el-checkbox>
          <el-checkbox v-model="form.is_buyer">买手用户</el-checkbox>
          <el-checkbox v-model="form.is_admin">管理员</el-checkbox>
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio label="active">正常</el-radio>
            <el-radio label="disabled">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getUsers, updateUser } from '../api'

const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const currentUserId = ref('')

const searchForm = reactive({
  user_id: '',
  role: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const users = ref([])

const form = reactive({
  user_id: '',
  nickname: '',
  is_vip: false,
  is_buyer: false,
  is_admin: false,
  status: 'active'
})

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

const loadUsers = async () => {
  loading.value = true
  try {
    const data = await getUsers({
      page: pagination.page,
      page_size: pagination.page_size
    })
    users.value = data.list || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('加载用户列表失败:', error)
  } finally {
    loading.value = false
  }
}

const resetSearch = () => {
  searchForm.user_id = ''
  searchForm.role = ''
  pagination.page = 1
  loadUsers()
}

const viewDetail = (row) => {
  ElMessage.info(`用户详情：${row.user_id}`)
}

const openEditDialog = (row) => {
  currentUserId.value = row.user_id
  Object.assign(form, {
    user_id: row.user_id,
    nickname: row.nickname || '',
    is_vip: row.is_vip || false,
    is_buyer: row.is_buyer || false,
    is_admin: row.is_admin || false,
    status: row.status || 'active'
  })
  dialogVisible.value = true
}

const submitForm = async () => {
  submitting.value = true
  try {
    await updateUser({
      user_id: currentUserId.value,
      nickname: form.nickname,
      is_vip: form.is_vip,
      is_buyer: form.is_buyer,
      is_admin: form.is_admin,
      status: form.status
    })
    ElMessage.success('修改成功')
    dialogVisible.value = false
    loadUsers()
  } catch (error) {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.users-page {
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

.text-gray {
  color: #909399;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
