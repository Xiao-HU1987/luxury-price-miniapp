<template>
  <div class="marketing-page">
    <el-tabs v-model="activeTab" class="marketing-tabs">
      <el-tab-pane label="优惠券" name="coupons">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>优惠券列表</span>
            </div>
          </template>
          
          <el-table :data="coupons" stripe v-loading="loading">
            <el-table-column prop="coupon_id" label="优惠券ID" width="120" />
            <el-table-column prop="title" label="标题" min-width="150" />
            <el-table-column label="类型" width="100">
              <template #default="{ row }">
                {{ getCouponType(row.type) }}
              </template>
            </el-table-column>
            <el-table-column label="优惠力度" width="120">
              <template #default="{ row }">
                {{ row.discount }}{{ row.type === 'percent' ? '%' : '元' }}
              </template>
            </el-table-column>
            <el-table-column label="适用国家" width="100">
              <template #default="{ row }">
                {{ row.country }}
              </template>
            </el-table-column>
            <el-table-column prop="store_name" label="适用门店" width="150" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'available' ? 'success' : 'info'" size="small">
                  {{ row.status === 'available' ? '可用' : '不可用' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="返点优惠" name="rebates">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>返点优惠列表</span>
            </div>
          </template>
          
          <el-table :data="rebates" stripe v-loading="loading2">
            <el-table-column prop="rebate_id" label="返点ID" width="120" />
            <el-table-column prop="title" label="标题" min-width="180" />
            <el-table-column label="国家" width="80">
              <template #default="{ row }">
                {{ row.country }}
              </template>
            </el-table-column>
            <el-table-column label="返点比例" width="100">
              <template #default="{ row }">
                {{ row.rate }}%
              </template>
            </el-table-column>
            <el-table-column label="VIP专属" width="100">
              <template #default="{ row }">
                <el-tag v-if="row.is_vip_only" type="warning" size="small">VIP专属</el-tag>
                <span v-else class="text-gray">全部用户</span>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
            <el-table-column label="有效期" width="200">
              <template #default="{ row }">
                {{ row.start_date }} ~ {{ row.end_date }}
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'available' ? 'success' : 'info'" size="small">
                  {{ row.status === 'available' ? '进行中' : '已结束' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="开屏广告" name="splashAds">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>开屏广告列表</span>
              <div class="header-actions">
                <el-button type="primary" @click="openAddSplashDialog">
                  <el-icon><ele-Plus /></el-icon> 添加广告
                </el-button>
              </div>
            </div>
          </template>
          
          <el-table :data="splashAds" stripe v-loading="splashLoading">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column label="广告图" width="120">
              <template #default="{ row }">
                <el-image
                  v-if="row.image_url"
                  :src="row.image_url"
                  :preview-src-list="[row.image_url]"
                  fit="cover"
                  style="width: 80px; height: 50px; border-radius: 4px;"
                />
                <span v-else class="text-gray">无图</span>
              </template>
            </el-table-column>
            <el-table-column prop="title" label="标题" min-width="150" />
            <el-table-column label="类型" width="80">
              <template #default="{ row }">
                {{ row.ad_type === 'image' ? '图片' : '视频' }}
              </template>
            </el-table-column>
            <el-table-column label="时长" width="80">
              <template #default="{ row }">
                {{ row.duration }}秒
              </template>
            </el-table-column>
            <el-table-column label="可跳过" width="80">
              <template #default="{ row }">
                <el-tag :type="row.skip_enabled ? 'success' : 'warning'" size="small">
                  {{ row.skip_enabled ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="每日上限" width="90">
              <template #default="{ row }">
                {{ row.daily_limit }}次
              </template>
            </el-table-column>
            <el-table-column label="展示/点击" width="120">
              <template #default="{ row }">
                <span style="color: #67c23a;">{{ row.show_count }}</span>
                /
                <span style="color: #e6a23c;">{{ row.click_count }}</span>
              </template>
            </el-table-column>
            <el-table-column label="排序" width="70">
              <template #default="{ row }">
                {{ row.sort_order }}
              </template>
            </el-table-column>
            <el-table-column label="有效期" width="200">
              <template #default="{ row }">
                <span v-if="row.start_time || row.end_time">
                  {{ formatDate(row.start_time) }} ~ {{ formatDate(row.end_time) }}
                </span>
                <span v-else class="text-gray">永久有效</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-switch
                  v-model="row.is_active"
                  :loading="row._toggling"
                  @change="toggleAd(row)"
                  active-text="启用"
                  inactive-text="禁用"
                  inline-prompt
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" link @click="openEditSplashDialog(row)">编辑</el-button>
                <el-button type="danger" size="small" link @click="deleteSplashAd(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <div class="pagination-wrap">
            <el-pagination
              v-model:current-page="splashPagination.page"
              v-model:page-size="splashPagination.page_size"
              :total="splashPagination.total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @size-change="loadSplashAds"
              @current-change="loadSplashAds"
            />
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="splashDialogVisible" :title="splashDialogTitle" width="600px" @closed="resetSplashForm">
      <el-form ref="splashFormRef" :model="splashForm" :rules="splashRules" label-width="100px">
        <el-form-item label="广告标题" prop="title">
          <el-input v-model="splashForm.title" placeholder="请输入广告标题" />
        </el-form-item>
        <el-form-item label="广告类型" prop="ad_type">
          <el-radio-group v-model="splashForm.ad_type">
            <el-radio label="image">图片</el-radio>
            <el-radio label="video">视频</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="图片URL" prop="image_url">
          <el-input v-model="splashForm.image_url" placeholder="请输入图片URL" />
          <div v-if="splashForm.image_url" class="preview-wrap">
            <el-image :src="splashForm.image_url" fit="contain" style="width: 200px; height: 120px;" />
          </div>
        </el-form-item>
        <el-form-item label="视频URL" v-if="splashForm.ad_type === 'video'">
          <el-input v-model="splashForm.video_url" placeholder="请输入视频URL" />
        </el-form-item>
        <el-form-item label="展示时长" prop="duration">
          <el-input-number v-model="splashForm.duration" :min="1" :max="30" />
          <span style="margin-left: 8px; color: #909399;">秒</span>
        </el-form-item>
        <el-form-item label="允许跳过" prop="skip_enabled">
          <el-switch v-model="splashForm.skip_enabled" />
        </el-form-item>
        <el-form-item label="每日上限" prop="daily_limit">
          <el-input-number v-model="splashForm.daily_limit" :min="0" :max="99" />
          <span style="margin-left: 8px; color: #909399;">次/天，0表示不限</span>
        </el-form-item>
        <el-form-item label="跳转类型" prop="link_type">
          <el-radio-group v-model="splashForm.link_type">
            <el-radio label="none">不跳转</el-radio>
            <el-radio label="page">内部页面</el-radio>
            <el-radio label="url">外部链接</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="跳转页面" v-if="splashForm.link_type === 'page'">
          <el-input v-model="splashForm.link_page" placeholder="如：/pages/index/index" />
        </el-form-item>
        <el-form-item label="跳转链接" v-if="splashForm.link_type === 'url'">
          <el-input v-model="splashForm.link_url" placeholder="https://..." />
        </el-form-item>
        <el-form-item label="排序权重" prop="sort_order">
          <el-input-number v-model="splashForm.sort_order" :min="0" :max="999" />
          <span style="margin-left: 8px; color: #909399;">数值越大越优先</span>
        </el-form-item>
        <el-form-item label="有效期">
          <el-date-picker
            v-model="splashDateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%;"
          />
        </el-form-item>
        <el-form-item label="状态" prop="is_active">
          <el-switch v-model="splashForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="splashDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="splashSubmitting" @click="submitSplashForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCoupons, getRebates, getSplashAds, createSplashAd, updateSplashAd, deleteSplashAd as deleteSplashAdApi, toggleSplashAd } from '../api'

const activeTab = ref('coupons')
const loading = ref(false)
const loading2 = ref(false)
const coupons = ref([])
const rebates = ref([])

const getCouponType = (type) => {
  const map = { discount: '满减', percent: '折扣', rebate: '返现' }
  return map[type] || type
}

const loadCoupons = async () => {
  loading.value = true
  try {
    const data = await getCoupons({ page: 1, page_size: 100 })
    coupons.value = data.list || []
  } catch (error) {
    console.error('加载优惠券失败:', error)
  } finally {
    loading.value = false
  }
}

const loadRebates = async () => {
  loading2.value = true
  try {
    const data = await getRebates({ page: 1, page_size: 100 })
    rebates.value = data.list || []
  } catch (error) {
    console.error('加载返点失败:', error)
  } finally {
    loading2.value = false
  }
}

const splashLoading = ref(false)
const splashAds = ref([])
const splashPagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const loadSplashAds = async () => {
  splashLoading.value = true
  try {
    const data = await getSplashAds({
      page: splashPagination.page,
      page_size: splashPagination.page_size
    })
    splashAds.value = data.list || []
    splashPagination.total = data.total || 0
  } catch (error) {
    console.error('加载开屏广告失败:', error)
    ElMessage.error('加载开屏广告失败')
  } finally {
    splashLoading.value = false
  }
}

const formatDate = (date) => {
  if (!date) return '不限'
  return String(date).substring(0, 16)
}

const toggleAd = async (row) => {
  row._toggling = true
  try {
    await toggleSplashAd(row.id)
    ElMessage.success(row.is_active ? '已启用' : '已禁用')
  } catch (error) {
    row.is_active = !row.is_active
    ElMessage.error('操作失败')
  } finally {
    row._toggling = false
  }
}

const splashDialogVisible = ref(false)
const splashFormRef = ref(null)
const splashSubmitting = ref(false)
const isEditSplash = ref(false)
const splashDateRange = ref([])

const splashForm = reactive({
  id: null,
  title: '',
  image_url: '',
  video_url: '',
  ad_type: 'image',
  duration: 5,
  skip_enabled: true,
  link_type: 'none',
  link_url: '',
  link_page: '',
  is_active: true,
  sort_order: 0,
  daily_limit: 1
})

const splashRules = {
  title: [{ required: true, message: '请输入广告标题', trigger: 'blur' }],
  image_url: [{ required: true, message: '请输入图片URL', trigger: 'blur' }],
  duration: [{ required: true, message: '请输入展示时长', trigger: 'blur' }]
}

const splashDialogTitle = computed(() => isEditSplash.value ? '编辑广告' : '添加广告')

const openAddSplashDialog = () => {
  isEditSplash.value = false
  splashDialogVisible.value = true
}

const openEditSplashDialog = (row) => {
  isEditSplash.value = true
  Object.assign(splashForm, row)
  if (row.start_time || row.end_time) {
    splashDateRange.value = [row.start_time, row.end_time]
  } else {
    splashDateRange.value = []
  }
  splashDialogVisible.value = true
}

const resetSplashForm = () => {
  splashFormRef.value?.resetFields()
  Object.assign(splashForm, {
    id: null,
    title: '',
    image_url: '',
    video_url: '',
    ad_type: 'image',
    duration: 5,
    skip_enabled: true,
    link_type: 'none',
    link_url: '',
    link_page: '',
    is_active: true,
    sort_order: 0,
    daily_limit: 1
  })
  splashDateRange.value = []
}

const submitSplashForm = async () => {
  if (!splashFormRef.value) return
  await splashFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    splashSubmitting.value = true
    try {
      const payload = { ...splashForm }
      if (splashDateRange.value && splashDateRange.value.length === 2) {
        payload.start_time = splashDateRange.value[0]
        payload.end_time = splashDateRange.value[1]
      } else {
        payload.start_time = null
        payload.end_time = null
      }
      
      if (isEditSplash.value) {
        await updateSplashAd(splashForm.id, payload)
        ElMessage.success('更新成功')
      } else {
        await createSplashAd(payload)
        ElMessage.success('创建成功')
      }
      
      splashDialogVisible.value = false
      loadSplashAds()
    } catch (error) {
      console.error('提交失败:', error)
      ElMessage.error('操作失败')
    } finally {
      splashSubmitting.value = false
    }
  })
}

const deleteSplashAd = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除广告"${row.title}"吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteSplashAdApi(row.id)
    ElMessage.success('删除成功')
    loadSplashAds()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadCoupons()
})
</script>

<style scoped>
.marketing-page {
  padding: 0;
}

.text-gray {
  color: #909399;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.preview-wrap {
  margin-top: 8px;
}
</style>
