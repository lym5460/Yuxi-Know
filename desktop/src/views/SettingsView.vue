<template>
  <div class="settings-view">
    <TitleBar transparent />
    <div class="settings-card">
      <h2 class="settings-title">服务器设置</h2>
      <p class="settings-desc">配置KGRAG-曼析服务端地址以连接您的智能体平台</p>

      <a-form layout="vertical" :model="form" @finish="handleSave">
        <a-form-item label="服务器地址" name="serverUrl"
          :rules="[{ required: true, message: '请输入服务器地址' }]">
          <a-input
            v-model:value="form.serverUrl"
            placeholder="http://192.168.1.100:5050"
            size="large"
          >
            <template #prefix>
              <Globe :size="16" style="color: var(--gray-400)" />
            </template>
          </a-input>
        </a-form-item>

        <a-form-item>
          <a-button type="primary" html-type="submit" :loading="testing" block size="large">
            {{ testing ? '连接测试中...' : '保存并连接' }}
          </a-button>
        </a-form-item>

        <a-alert v-if="errorMsg" type="error" :message="errorMsg" show-icon closable
          @close="errorMsg = ''" style="margin-top: 12px" />
        <a-alert v-if="successMsg" type="success" :message="successMsg" show-icon
          style="margin-top: 12px" />
      </a-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Globe } from 'lucide-vue-next'
import { useServerStore } from '@/stores/server'
import TitleBar from '@/components/TitleBar.vue'

const router = useRouter()
const serverStore = useServerStore()

const form = reactive({
  serverUrl: ''
})
const testing = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

onMounted(() => {
  form.serverUrl = serverStore.serverUrl || ''
})

async function handleSave() {
  const url = form.serverUrl.replace(/\/+$/, '')
  if (!url) return

  testing.value = true
  errorMsg.value = ''
  successMsg.value = ''

  try {
    // 测试连接：调用健康检查接口
    const response = await fetch(`${url}/api/system/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(10000)
    })

    if (!response.ok) {
      throw new Error(`服务器返回 ${response.status}`)
    }

    // 保存配置
    serverStore.setServerUrl(url)
    successMsg.value = '连接成功！'

    // 跳转到登录页
    setTimeout(() => {
      router.push('/login')
    }, 800)
  } catch (e) {
    if (e.name === 'TimeoutError') {
      errorMsg.value = '连接超时，请检查服务器地址是否正确'
    } else if (e.name === 'TypeError' && e.message.includes('fetch')) {
      errorMsg.value = '无法连接到服务器，请检查地址和网络'
    } else {
      errorMsg.value = `连接失败: ${e.message}`
    }
  } finally {
    testing.value = false
  }
}
</script>

<style lang="less" scoped>
.settings-view {
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

.settings-card {
  width: 420px;
  padding: 40px;
  background: var(--glass-bg);
  border-radius: 12px;
  border: 1px solid var(--glass-border);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3), var(--glow-primary-sm);
  position: relative;
  backdrop-filter: blur(12px);
}

.settings-title {
  margin: 0 0 4px;
  font-size: 22px;
  font-weight: 600;
  color: var(--color-primary-500);
  text-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
}

.settings-desc {
  margin: 0 0 28px;
  font-size: 14px;
  color: var(--gray-500);
}
</style>
