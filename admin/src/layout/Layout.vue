<template>
  <el-container class="layout-container">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <img src="../assets/vite.svg" alt="logo" v-if="!isCollapse" />
        <span v-if="!isCollapse">管理后台</span>
        <el-icon v-else><ele-Coffee /></el-icon>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        router
        class="menu"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/dashboard">
          <el-icon><ele-DataBoard /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>
        
        <el-sub-menu index="/products">
          <template #title>
            <el-icon><ele-Goods /></el-icon>
            <span>商品管理</span>
          </template>
          <el-menu-item index="/products">商品列表</el-menu-item>
        </el-sub-menu>
        
        <el-menu-item index="/users">
          <el-icon><ele-User /></el-icon>
          <template #title>用户管理</template>
        </el-menu-item>
        
        <el-menu-item index="/orders">
          <el-icon><ele-ShoppingCart /></el-icon>
          <template #title>订单管理</template>
        </el-menu-item>
        
        <el-menu-item index="/buyers">
          <el-icon><ele-Shop /></el-icon>
          <template #title>买手管理</template>
        </el-menu-item>
        
        <el-menu-item index="/demands">
          <el-icon><ele-Document /></el-icon>
          <template #title>需求管理</template>
        </el-menu-item>
        
        <el-menu-item index="/marketing">
          <el-icon><ele-Ticket /></el-icon>
          <template #title>营销管理</template>
        </el-menu-item>
        
        <el-menu-item index="/stores">
          <el-icon><ele-OfficeBuilding /></el-icon>
          <template #title>门店管理</template>
        </el-menu-item>
        
        <el-menu-item index="/exchange">
          <el-icon><ele-Coin /></el-icon>
          <template #title>汇率管理</template>
        </el-menu-item>
        
        <el-menu-item index="/logs">
          <el-icon><ele-DocumentCopy /></el-icon>
          <template #title>日志管理</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <el-container>
      <!-- 头部 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse">
            <ele-Expand v-if="isCollapse" />
            <ele-Fold v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRoute.meta?.title">{{ currentRoute.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" icon="ele-UserFilled" />
              <span class="username">{{ adminInfo?.nickname || '管理员' }}</span>
              <el-icon><ele-ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人设置</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <!-- 主内容区 -->
      <el-main class="main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()

const isCollapse = ref(false)
const adminInfo = ref(null)

const activeMenu = computed(() => route.path)
const currentRoute = computed(() => route)

onMounted(() => {
  const info = localStorage.getItem('admin_info')
  if (info) {
    adminInfo.value = JSON.parse(info)
  }
})

const handleCommand = (command) => {
  if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_info')
      router.push('/login')
    }).catch(() => {})
  } else if (command === 'profile') {
    ElMessageBox.info('个人设置功能开发中...')
  }
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.aside {
  background-color: #304156;
  transition: width 0.3s;
  overflow-x: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid #3d4a5c;
}

.logo img {
  width: 32px;
  height: 32px;
  margin-right: 8px;
}

.menu {
  border-right: none;
}

.header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #666;
}

.collapse-btn:hover {
  color: #409EFF;
}

.header-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 0 8px;
  border-radius: 4px;
}

.user-info:hover {
  background-color: #f5f7fa;
}

.username {
  color: #333;
  font-size: 14px;
}

.main {
  background-color: #f0f2f5;
  padding: 20px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
