<template>
  <div class="exchange-page">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>汇率管理</span>
          <el-button type="primary" @click="showEditDialog = true">
            <el-icon><ele-Edit /></el-icon> 编辑汇率
          </el-button>
        </div>
      </template>
      
      <el-alert
        title="汇率说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px;"
      >
        汇率以人民币（CNY）为基准，表示1元人民币可兑换的外币数量。汇率数据用于全球奢侈品价格的统一换算。
      </el-alert>
      
      <div class="rate-grid">
        <el-card v-for="rate in rates" :key="rate.currency" class="rate-card">
          <div class="rate-header">
            <span class="country-flag">{{ rate.flag }}</span>
            <span class="currency-name">{{ rate.currencyName }}</span>
          </div>
          <div class="rate-value">
            {{ rate.rate }}
          </div>
          <div class="rate-code">{{ rate.currency }}</div>
        </el-card>
      </div>
    </el-card>
    
    <!-- 编辑汇率对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑汇率" width="600px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item v-for="rate in editRates" :key="rate.currency" :label="rate.currencyName">
          <el-input-number v-model="rate.rate" :precision="4" :step="0.0001" :min="0" style="width: 200px;" />
          <span style="margin-left: 8px; color: #909399;">{{ rate.currency }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveRates">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getExchangeRates, updateExchangeRate } from '../api'

const showEditDialog = ref(false)
const rates = ref([])
const editRates = ref([])

const allCurrencies = [
  { currency: 'USD', currencyName: '美元', flag: '🇺🇸' },
  { currency: 'EUR', currencyName: '欧元', flag: '🇪🇺' },
  { currency: 'GBP', currencyName: '英镑', flag: '🇬🇧' },
  { currency: 'JPY', currencyName: '日元', flag: '🇯🇵' },
  { currency: 'KRW', currencyName: '韩元', flag: '🇰🇷' },
  { currency: 'HKD', currencyName: '港币', flag: '🇭🇰' },
  { currency: 'SGD', currencyName: '新加坡元', flag: '🇸🇬' },
  { currency: 'AUD', currencyName: '澳元', flag: '🇦🇺' },
  { currency: 'CHF', currencyName: '瑞士法郎', flag: '🇨🇭' },
  { currency: 'CAD', currencyName: '加元', flag: '🇨🇦' },
  { currency: 'THB', currencyName: '泰铢', flag: '🇹🇭' }
]

const loadRates = async () => {
  try {
    const data = await getExchangeRates()
    const currentRates = data.rates || {}
    rates.value = allCurrencies.map(c => ({
      ...c,
      rate: currentRates[c.currency] || 0
    }))
    editRates.value = JSON.parse(JSON.stringify(rates.value))
  } catch (error) {
    console.error('加载汇率失败:', error)
  }
}

const saveRates = async () => {
  try {
    const ratesObj = {}
    editRates.value.forEach(r => {
      ratesObj[r.currency] = r.rate
    })
    await updateExchangeRate({ rates: ratesObj })
    ElMessage.success('汇率保存成功')
    showEditDialog.value = false
    loadRates()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

onMounted(() => {
  loadRates()
})
</script>

<style scoped>
.exchange-page {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rate-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}

.rate-card {
  text-align: center;
}

.rate-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 12px;
}

.country-flag {
  font-size: 24px;
}

.currency-name {
  font-size: 14px;
  color: #606266;
}

.rate-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.rate-code {
  font-size: 12px;
  color: #909399;
}
</style>
