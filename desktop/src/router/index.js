import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useServerStore } from '@/stores/server'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      redirect: '/chat'
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/SettingsView.vue')
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue')
    },
    {
      path: '/chat',
      name: 'Chat',
      component: () => import('@/views/ChatView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/video',
      name: 'Video',
      component: () => import('@/views/VideoWindow.vue')
    }
  ]
})

router.beforeEach((to, _from, next) => {
  const serverStore = useServerStore()
  const userStore = useUserStore()

  // 视频窗口不做拦截
  if (to.path === '/video') {
    next()
    return
  }

  // 未配置服务器地址 → 跳转设置页
  if (!serverStore.isConfigured && to.path !== '/settings') {
    next('/settings')
    return
  }

  // 需要认证但未登录 → 跳转登录页
  if (to.meta.requiresAuth && !userStore.isLoggedIn) {
    next('/login')
    return
  }

  // 已登录访问登录页 → 跳转智能体页
  if (to.path === '/login' && userStore.isLoggedIn) {
    next('/chat')
    return
  }

  next()
})

export default router
