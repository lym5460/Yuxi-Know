<template>
  <div class="login-view">
    <TitleBar transparent />
    <div class="login-card">
      <h2 class="login-title">登录KGRAG-曼析</h2>
      <p class="login-server">
        <Globe :size="14" />
        <span>{{ serverStore.serverUrl }}</span>
        <a class="change-link" @click="goSettings">更改</a>
      </p>

      <a-form layout="vertical" :model="form" @finish="handleLogin">
        <a-form-item label="账号" name="loginId"
          :rules="[{ required: true, message: '请输入账号' }]">
          <a-input v-model:value="form.loginId" placeholder="用户名或手机号" size="large" />
        </a-form-item>

        <a-form-item label="密码" name="password"
          :rules="[{ required: true, message: '请输入密码' }]">
          <a-input-password v-model:value="form.password" placeholder="密码" size="large"
            @pressEnter="handleLogin" />
        </a-form-item>

        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="loading" block size="large">
            登录
          </a-button>
        </a-form-item>

        <a-alert v-if="errorMsg" type="error" :message="errorMsg" show-icon closable
          @close="errorMsg = ''" />
      </a-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Globe } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { useServerStore } from '@/stores/server'
import TitleBar from '@/components/TitleBar.vue'

const router = useRouter()
const userStore = useUserStore()
const serverStore = useServerStore()

const form = reactive({
  loginId: '',
  password: ''
})
const loading = ref(false)
const errorMsg = ref('')

function goSettings() {
  router.push('/settings')
}

async function handleLogin() {
  if (!form.loginId || !form.password) return

  loading.value = true
  errorMsg.value = ''

  try {
    await userStore.login({ loginId: form.loginId, password: form.password })
    router.push('/chat')
  } catch (e) {
    if (e.status === 423) {
      errorMsg.value = e.message || '账户已被锁定，请稍后重试'
    } else {
      errorMsg.value = e.message || '登录失败'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style lang="less" scoped>
.login-view {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  background: var(--gray-0);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse at 20% 50%, rgba(0, 212, 255, 0.06) 0%, transparent 50%),
      radial-gradient(ellipse at 80% 50%, rgba(0, 140, 255, 0.04) 0%, transparent 50%);
    pointer-events: none;
  }
}

.login-card {
  width: 400px;
  padding: 40px;
  background: var(--glass-bg);
  border-radius: 12px;
  border: 1px solid var(--glass-border);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3), var(--glow-primary-sm);
  position: relative;
  backdrop-filter: blur(12px);
}

.login-title {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 600;
  color: var(--color-primary-500);
  text-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
}

.login-server {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 28px;
  font-size: 13px;
  color: var(--gray-500);

  .change-link {
    margin-left: auto;
    color: var(--color-primary-500);
    cursor: pointer;
    &:hover {
      text-decoration: underline;
      text-shadow: 0 0 6px rgba(0, 212, 255, 0.4);
    }
  }
}
</style>
