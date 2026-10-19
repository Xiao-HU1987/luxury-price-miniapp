<template>
  <div class="buyers-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>买手管理</span>
        </div>
      </template>
      
      <el-table :data="buyers" stripe v-loading="loading">
        <el-table-column prop="buyer_id" label="买手ID" width="120" />
        <el-table-column prop="name" label="买手名称" width="150" />
        <el-table-column label="国家/地区" width="100">
          <template #default="{ row }">
            {{ getCountryName(row.country) }} {{ getCountryFlag(row.country) }}
          </template>
        </el-table-column>
        <el-table-column label="评分" width="100">
          <template #default="{ row }">
            <el-rate v-model="row.rating" disabled text-color="#ff9900" />
          </template>
        </el-table-column>
        <el-table-column prop="orders" label="完成订单" width="100" />
        <el-table-column prop="fee_rate" label="服务费" width="80">
          <template #default="{ row }">
            {{ row.fee_rate }}%
          </template>
        </el-table-column>
        <el-table-column prop="delivery_days" label="到货天数" width="100" />
        <el-table-column prop="intro" label="简介" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="viewDetail(row)">详情</el-button>
            <el-button type="danger" size="small" link @click="deleteBuyer(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getBuyers, deleteBuyer as delBuyer } from '../api'

const loading = ref(false)
const buyers = ref([])

const countryMap = {
  JP: { name: '日本', flag: '🇯🇵' },
  FR: { name: '法国', flag: '🇫🇷' },
  HK: { name: '香港', flag: '🇭🇰' },
  KR: { name: '韩国', flag: '🇰🇷' },
  UK: { name: '英国', flag: '🇬🇧' },
  US: { name: '美国', flag: '🇺🇸' },
  IT: { name: '意大利', flag: '🇮🇹' }
}

const getCountryName = (code) => countryMap[code]?.name || code
const getCountryFlag = (code) => countryMap[code]?.flag || ''

const loadBuyers = async () => {
  loading.value = true
  try {
    const data = await getBuyers({ page: 1, page_size: 100 })
    buyers.value = data.list || []
  } catch (error) {
    console.error('加载买手列表失败:', error)
  } finally {
    loading.value = false
  }
}

const viewDetail = (row) => {
  ElMessageBox.alert(
    `<p><strong>买手ID：</strong>${row.buyer_id}</p>
     <p><strong>名称：</strong>${row.name}</p>
     <p><strong>国家：</strong>${getCountryName(row.country)}</p>
     <p><strong>评分：</strong>${row.rating}星</p>
     <p><strong>服务费：</strong>${row.fee_rate}%</p>
     <p><strong>到货天数：</strong>${row.delivery_days}天</p>
     <p><strong>简介：</strong>${row.intro}</p>`,
    '买手详情',
    { dangerouslyUseHTMLString: true }
  )
}

const deleteBuyer = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除买手 "${row.name}" 吗？`, '提示', { type: 'warning' })
    await delBuyer(row.buyer_id)
    ElMessage.success('删除成功')
    loadBuyers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadBuyers()
})
</script>

<style scoped>
.buyers-page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
