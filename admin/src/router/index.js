import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/',
    component: () => import('../layout/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '仪表盘', icon: 'DataBoard' }
      },
      {
        path: 'products',
        name: 'Products',
        component: () => import('../views/Products.vue'),
        meta: { title: '商品管理', icon: 'Goods' }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/Users.vue'),
        meta: { title: '用户管理', icon: 'User' }
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('../views/Orders.vue'),
        meta: { title: '订单管理', icon: 'ShoppingCart' }
      },
      {
        path: 'buyers',
        name: 'Buyers',
        component: () => import('../views/Buyers.vue'),
        meta: { title: '买手管理', icon: 'Shop' }
      },
      {
        path: 'demands',
        name: 'Demands',
        component: () => import('../views/Demands.vue'),
        meta: { title: '需求管理', icon: 'Document' }
      },
      {
        path: 'marketing',
        name: 'Marketing',
        component: () => import('../views/Marketing.vue'),
        meta: { title: '营销管理', icon: 'Ticket' }
      },
      {
        path: 'stores',
        name: 'Stores',
        component: () => import('../views/Stores.vue'),
        meta: { title: '门店管理', icon: 'OfficeBuilding' }
      },
      {
        path: 'exchange',
        name: 'Exchange',
        component: () => import('../views/Exchange.vue'),
        meta: { title: '汇率管理', icon: 'Coin' }
      },
      {
        path: 'trino',
        name: 'TrinoData',
        component: () => import('../views/TrinoData.vue'),
        meta: { title: 'Trino数据', icon: 'Coin' }
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('../views/Logs.vue'),
        meta: { title: '日志管理', icon: 'DocumentCopy' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - 管理后台` : '管理后台'
  
  const token = localStorage.getItem('admin_token')
  if (to.path !== '/login' && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
