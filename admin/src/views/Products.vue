<template>
  <div class="products-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>商品管理</span>
          <div class="header-actions">
            <el-button type="primary" @click="openAddDialog">
              <el-icon><ele-Plus /></el-icon> 添加商品
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- 搜索栏 -->
      <el-form inline class="search-form">
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="商品名称/货号" clearable @keyup.enter="loadProducts" />
        </el-form-item>
        <el-form-item label="品牌">
          <el-select v-model="searchForm.brand_id" placeholder="选择品牌" clearable>
            <el-option v-for="brand in brands" :key="brand.brand_id" :label="brand.name_cn" :value="brand.brand_id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadProducts">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
      
      <!-- 商品表格 -->
      <el-table :data="products" stripe v-loading="loading">
        <el-table-column prop="spu_id" label="SPU ID" width="120" />
        <el-table-column prop="brand_name" label="品牌" width="100" />
        <el-table-column prop="name" label="商品名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="article_no" label="货号" width="120" />
        <el-table-column label="价格范围" width="150">
          <template #default="{ row }">
            <span v-if="row.min_price && row.min_price > 0">
              ¥{{ row.min_price }} ~ ¥{{ row.max_price }}
            </span>
            <span v-else class="text-gray">暂无价格</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '在售' : '下架' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="viewDetail(row)">详情</el-button>
            <el-button type="warning" size="small" link @click="openEditDialog(row)">编辑</el-button>
            <el-button type="danger" size="small" link @click="deleteProduct(row)">删除</el-button>
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
          @size-change="loadProducts"
          @current-change="loadProducts"
        />
      </div>
    </el-card>
    
    <!-- 商品详情抽屉 -->
    <el-drawer v-model="detailVisible" title="商品详情" size="600px">
      <div v-if="currentProduct" class="product-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="SPU ID">{{ currentProduct.spu_id }}</el-descriptions-item>
          <el-descriptions-item label="品牌">{{ currentProduct.brand_name }}</el-descriptions-item>
          <el-descriptions-item label="商品名称" :span="2">{{ currentProduct.name }}</el-descriptions-item>
          <el-descriptions-item label="英文名" :span="2">{{ currentProduct.name_en || '-' }}</el-descriptions-item>
          <el-descriptions-item label="货号">{{ currentProduct.article_no }}</el-descriptions-item>
          <el-descriptions-item label="品类">{{ currentProduct.category_id }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ currentProduct.description || '-' }}</el-descriptions-item>
        </el-descriptions>
        
        <h4 class="sku-title">SKU列表</h4>
        <el-table :data="currentProduct.skus" size="small">
          <el-table-column prop="sku_id" label="SKU ID" width="120" />
          <el-table-column prop="name" label="规格" />
          <el-table-column prop="color" label="颜色" width="100" />
          <el-table-column prop="size" label="尺寸" width="100" />
          <el-table-column label="价格" width="150">
            <template #default="{ row }">
              <span v-if="row.prices && row.prices.length">
                <span v-for="p in row.prices" :key="p.id" class="price-tag">
                  {{ p.country }}: ¥{{ p.price }}
                </span>
              </span>
              <span v-else class="text-gray">暂无</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px" @closed="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="品牌" prop="brand_id">
          <el-select v-model="form.brand_id" placeholder="选择品牌" style="width: 100%;">
            <el-option v-for="brand in brands" :key="brand.brand_id" :label="brand.name_cn" :value="brand.brand_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="商品名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入商品名称" />
        </el-form-item>
        <el-form-item label="英文名称">
          <el-input v-model="form.name_en" placeholder="请输入英文名称" />
        </el-form-item>
        <el-form-item label="货号" prop="article_no">
          <el-input v-model="form.article_no" placeholder="请输入货号" />
        </el-form-item>
        <el-form-item label="品类">
          <el-input v-model="form.category_id" placeholder="请输入品类" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入商品描述" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio label="active">在售</el-radio>
            <el-radio label="inactive">下架</el-radio>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { searchProducts, getBrands, getProductDetail, deleteSpu, createSpu, updateSpu } from '../api'

const loading = ref(false)
const detailVisible = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const isEdit = ref(false)
const currentProduct = ref(null)
const currentSpuId = ref('')

const searchForm = reactive({
  keyword: '',
  brand_id: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const products = ref([])
const brands = ref([])

const form = reactive({
  brand_id: '',
  name: '',
  name_en: '',
  article_no: '',
  category_id: '',
  description: '',
  status: 'active'
})

const rules = {
  brand_id: [{ required: true, message: '请选择品牌', trigger: 'change' }],
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  article_no: [{ required: true, message: '请输入货号', trigger: 'blur' }]
}

const dialogTitle = computed(() => isEdit.value ? '编辑商品' : '添加商品')

const loadProducts = async () => {
  loading.value = true
  try {
    const data = await searchProducts({
      page: pagination.page,
      page_size: pagination.page_size,
      keyword: searchForm.keyword || undefined,
      brand_id: searchForm.brand_id || undefined
    })
    products.value = data.list || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('加载商品列表失败:', error)
  } finally {
    loading.value = false
  }
}

const loadBrands = async () => {
  try {
    const data = await getBrands()
    brands.value = data || []
  } catch (error) {
    console.error('加载品牌列表失败:', error)
  }
}

const resetSearch = () => {
  searchForm.keyword = ''
  searchForm.brand_id = ''
  pagination.page = 1
  loadProducts()
}

const viewDetail = async (row) => {
  try {
    const data = await getProductDetail(row.spu_id)
    currentProduct.value = data
    detailVisible.value = true
  } catch (error) {
    ElMessage.error('加载商品详情失败')
  }
}

const openAddDialog = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

const openEditDialog = async (row) => {
  isEdit.value = true
  currentSpuId.value = row.spu_id
  try {
    const data = await getProductDetail(row.spu_id)
    Object.assign(form, {
      brand_id: data.brand_id || '',
      name: data.name || '',
      name_en: data.name_en || '',
      article_no: data.article_no || '',
      category_id: data.category_id || '',
      description: data.description || '',
      status: data.status || 'active'
    })
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error('加载商品信息失败')
  }
}

const resetForm = () => {
  Object.assign(form, {
    brand_id: '',
    name: '',
    name_en: '',
    article_no: '',
    category_id: '',
    description: '',
    status: 'active'
  })
  formRef.value?.clearValidate()
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    submitting.value = true
    try {
      if (isEdit.value) {
        await updateSpu(currentSpuId.value, form)
        ElMessage.success('修改成功')
      } else {
        await createSpu(form)
        ElMessage.success('添加成功')
      }
      dialogVisible.value = false
      loadProducts()
    } catch (error) {
      ElMessage.error('操作失败')
    } finally {
      submitting.value = false
    }
  })
}

const deleteProduct = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除商品 "${row.name}" 吗？`, '提示', { type: 'warning' })
    await deleteSpu(row.spu_id)
    ElMessage.success('删除成功')
    loadProducts()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadProducts()
  loadBrands()
})
</script>

<style scoped>
.products-page {
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

.product-detail {
  padding: 0 10px;
}

.sku-title {
  margin: 20px 0 10px;
  font-size: 16px;
  color: #303133;
}

.price-tag {
  display: inline-block;
  margin-right: 8px;
  padding: 2px 6px;
  background: #f0f9ff;
  border-radius: 4px;
  font-size: 12px;
  color: #409EFF;
}
</style>
