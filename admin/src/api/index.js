import request from '../utils/request'

// 管理员登录
export const adminLogin = (data) => {
  return request.post('/api/admin/login', data)
}

// 获取仪表盘数据
export const getDashboardStats = () => {
  return request.get('/api/admin/dashboard/stats')
}

// 获取订单趋势
export const getOrderTrend = (days = 7) => {
  return request.get('/api/admin/dashboard/order-trend', { params: { days } })
}

// 获取流量趋势
export const getTrafficTrend = (days = 7) => {
  return request.get('/api/admin/dashboard/traffic-trend', { params: { days } })
}

// 获取热门商品
export const getHotProducts = (limit = 10) => {
  return request.get('/api/admin/dashboard/hot-products', { params: { limit } })
}

// 用户管理
export const getUsers = (params) => request.get('/api/admin/users', { params })
export const getUserById = (id) => request.get(`/api/admin/users`, { params: { user_id: id } })
export const updateUser = (data) => request.put('/api/admin/users', data)

// 订单管理
export const getOrders = (params) => request.get('/api/order/list', { params })
export const getOrderById = (id) => request.get(`/api/order/${id}`)
export const updateOrderStatus = (id, status) => request.put(`/api/order/${id}/status`, null, { params: { status_value: status } })
export const updateOrder = (id, data) => request.put(`/api/order/${id}`, data)

// 商品管理
export const getBrands = (params) => request.get('/api/product/brands', { params })
export const getBrandById = (id) => request.get(`/api/product/brands/${id}`)
export const createBrand = (data) => request.post('/api/product/brands', data)
export const updateBrand = (id, data) => request.put(`/api/product/brands/${id}`, data)
export const deleteBrand = (id) => request.delete(`/api/product/brands/${id}`)

export const getCategories = (params) => request.get('/api/product/categories', { params })
export const getCategoryById = (id) => request.get(`/api/product/categories/${id}`)
export const createCategory = (data) => request.post('/api/product/categories', data)
export const updateCategory = (id, data) => request.put(`/api/product/categories/${id}`, data)
export const deleteCategory = (id) => request.delete(`/api/product/categories/${id}`)

export const getSpus = (params) => request.get('/api/product/spus', { params })
export const getSpuById = (id) => request.get(`/api/product/spus/${id}`)
export const createSpu = (data) => request.post('/api/product/spus', data)
export const updateSpu = (id, data) => request.put(`/api/product/spus/${id}`, data)
export const deleteSpu = (id) => request.delete(`/api/product/spus/${id}`)

export const getSkus = (params) => request.get('/api/product/skus', { params })
export const getSkuById = (id) => request.get(`/api/product/skus/${id}`)
export const createSku = (data) => request.post('/api/product/skus', data)
export const updateSku = (id, data) => request.put(`/api/product/skus/${id}`, data)
export const deleteSku = (id) => request.delete(`/api/product/skus/${id}`)

export const getSkuPrices = (params) => request.get('/api/product/sku-prices', { params })
export const createSkuPrice = (data) => request.post('/api/product/sku-prices', data)
export const updateSkuPrice = (id, data) => request.put(`/api/product/sku-prices/${id}`, data)
export const deleteSkuPrice = (id) => request.delete(`/api/product/sku-prices/${id}`)

export const searchProducts = (params) => request.get('/api/product/search', { params })
export const getProductDetail = (id) => request.get(`/api/product/product-detail/${id}`)

// 买手管理
export const getBuyers = (params) => request.get('/api/buyer/list', { params })
export const getBuyerById = (id) => request.get(`/api/buyer/${id}`)
export const createBuyer = (data) => request.post('/api/buyer', data)
export const updateBuyer = (id, data) => request.put(`/api/buyer/${id}`, data)
export const deleteBuyer = (id) => request.delete(`/api/buyer/${id}`)

// 需求管理
export const getDemands = (params) => request.get('/api/demand/list', { params })
export const getDemandById = (id) => request.get(`/api/demand/${id}`)
export const createDemand = (data) => request.post('/api/demand', data)
export const updateDemand = (id, data) => request.put(`/api/demand/${id}`, data)
export const deleteDemand = (id) => request.delete(`/api/demand/${id}`)

// 门店管理
export const getStores = (params) => request.get('/api/store/list', { params })
export const getStoreById = (id) => request.get(`/api/store/${id}`)
export const createStore = (data) => request.post('/api/store', data)
export const updateStore = (id, data) => request.put(`/api/store/${id}`, data)
export const deleteStore = (id) => request.delete(`/api/store/${id}`)

// 优惠券管理
export const getCoupons = (params) => request.get('/api/coupon/list', { params })
export const getCouponById = (id) => request.get(`/api/coupon/${id}`)
export const createCoupon = (data) => request.post('/api/coupon', data)
export const updateCoupon = (id, data) => request.put(`/api/coupon/${id}`, data)
export const deleteCoupon = (id) => request.delete(`/api/coupon/${id}`)

// 返点管理
export const getRebates = (params) => request.get('/api/rebate/list', { params })
export const getRebateById = (id) => request.get(`/api/rebate/${id}`)
export const createRebate = (data) => request.post('/api/rebate', data)
export const updateRebate = (id, data) => request.put(`/api/rebate/${id}`, data)
export const deleteRebate = (id) => request.delete(`/api/rebate/${id}`)

// 汇率管理
export const getExchangeRates = () => request.get('/api/exchange/rates')
export const updateExchangeRate = (data) => request.put('/api/exchange/rates', data)

// 日志管理
export const getAccessLogs = (params) => request.get('/api/log/access/list', { params })
export const getOperationLogs = (params) => request.get('/api/log/operation/list', { params })

// 开屏广告管理
export const getSplashAds = (params) => request.get('/api/admin/splash-ads', { params })
export const getSplashAdById = (id) => request.get(`/api/admin/splash-ads/${id}`)
export const createSplashAd = (data) => request.post('/api/admin/splash-ads', data)
export const updateSplashAd = (id, data) => request.put(`/api/admin/splash-ads/${id}`, data)
export const deleteSplashAd = (id) => request.delete(`/api/admin/splash-ads/${id}`)
export const toggleSplashAd = (id) => request.patch(`/api/admin/splash-ads/${id}/toggle`)
