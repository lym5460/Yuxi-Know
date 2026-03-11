<template>
  <div class="chat-view">
    <!-- 侧边栏 -->
    <div class="sidebar">
      <div class="sidebar-header">
        <div class="agent-selector" @click="showAgentModal = true">
          <Bot :size="18" />
          <span class="agent-name">{{ agentStore.currentAgentName || '选择智能体' }}</span>
          <ChevronDown :size="14" />
        </div>
        <button class="icon-btn" @click="handleNewChat" title="新对话">
          <Plus :size="18" />
        </button>
      </div>

      <div class="thread-list">
        <div
          v-for="thread in chatStore.threads"
          :key="thread.id"
          class="thread-item"
          :class="{ active: thread.id === chatStore.currentThreadId }"
          @click="switchThread(thread.id)"
        >
          <MessageSquare :size="14" />
          <span class="thread-title">{{ thread.title || '新的对话' }}</span>
        </div>
        <div v-if="!chatStore.threads.length" class="thread-empty">
          暂无对话
        </div>
      </div>

      <div class="sidebar-footer">
        <button class="icon-btn" @click="$router.push('/settings')" title="设置">
          <Settings :size="18" />
        </button>
        <button class="icon-btn" @click="handleLogout" title="退出登录">
          <LogOut :size="18" />
        </button>
      </div>
    </div>

    <!-- 主聊天区 -->
    <div class="chat-main">
      <!-- 消息列表 -->
      <div class="messages-area" ref="messagesRef">
        <div v-if="chatStore.isLoadingMessages" class="loading-state">
          <LoaderCircle :size="24" class="spin" />
          <span>加载消息中...</span>
        </div>

        <div v-else-if="!chatStore.messages.length" class="empty-state">
          <Bot :size="48" class="empty-icon" />
          <h3>{{ agentStore.currentAgentName || '智能助手' }}</h3>
          <p>{{ agentStore.currentAgent?.description || '有什么可以帮你的？' }}</p>
          <div v-if="exampleQuestions.length" class="examples">
            <button
              v-for="(q, i) in exampleQuestions"
              :key="i"
              class="example-btn"
              @click="sendMessage(q)"
            >
              {{ q }}
            </button>
          </div>
        </div>

        <template v-else>
          <ChatMessage
            v-for="(msg, i) in chatStore.messages"
            :key="i"
            :message="msg"
            :agent-name="agentStore.currentAgentName"
            :is-streaming="chatStore.isProcessing && i === chatStore.messages.length - 1 && msg.role === 'assistant'"
          />
        </template>
      </div>

      <!-- 语音输入区 -->
      <div v-if="isVoiceAgent" class="input-area voice-input-area">
        <div v-if="voiceInterimTranscript" class="voice-interim">
          {{ voiceInterimTranscript }}
        </div>
        <div class="voice-controls">
          <span class="voice-status-text">{{ voiceStatusText }}</span>
          <button
            class="voice-btn"
            :class="{ recording: voiceRecording, error: voiceStatus === 'error' }"
            @click="toggleVoiceRecording"
          >
            <div v-if="voiceRecording" class="voice-level" :style="{ transform: `scale(${1 + voiceAudioLevel * 0.8})` }"></div>
            <Mic v-if="!voiceRecording" :size="24" />
            <PhoneOff v-else :size="24" />
          </button>
        </div>
      </div>

      <!-- 文本输入区 -->
      <div v-else class="input-area">
        <div class="input-wrapper">
          <textarea
            ref="inputRef"
            v-model="userInput"
            :disabled="chatStore.isProcessing"
            placeholder="输入消息..."
            rows="1"
            @keydown.enter.exact.prevent="handleSend"
            @input="autoResize"
          />
          <button
            class="send-btn"
            :disabled="!userInput.trim() || chatStore.isProcessing"
            @click="handleSend"
          >
            <SendHorizontal v-if="!chatStore.isProcessing" :size="18" />
            <LoaderCircle v-else :size="18" class="spin" />
          </button>
        </div>
      </div>
    </div>

    <!-- 智能体选择弹窗 -->
    <a-modal
      v-model:open="showAgentModal"
      title="选择智能体"
      :footer="null"
      :width="600"
    >
      <div class="agent-grid">
        <div
          v-for="agent in agentStore.agents"
          :key="agent.id"
          class="agent-card"
          :class="{ selected: agent.id === agentStore.selectedAgentId }"
          @click="selectAgent(agent.id)"
        >
          <div class="agent-card-name">{{ agent.name }}</div>
          <div class="agent-card-desc">{{ agent.description }}</div>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import {
  Bot, ChevronDown, Plus, MessageSquare, Settings, LogOut,
  SendHorizontal, LoaderCircle, Mic, MicOff, PhoneOff
} from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { useAgentStore } from '@/stores/agent'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import { agentApi } from '@/apis'
import { createVoiceWebSocket, sendAudio, sendControl, saveVoiceMessage } from '@/apis/voice_api'
import { useAudioCapture } from '@/composables/useAudioCapture'
import { useAudioPlayer } from '@/composables/useAudioPlayer'
import ChatMessage from '@/components/ChatMessage.vue'

const router = useRouter()
const agentStore = useAgentStore()
const chatStore = useChatStore()
const userStore = useUserStore()

const userInput = ref('')
const showAgentModal = ref(false)
const messagesRef = ref(null)
const inputRef = ref(null)

const exampleQuestions = computed(() => {
  return agentStore.currentAgent?.examples || []
})

// 语音模式
const isVoiceAgent = computed(() => {
  const caps = agentStore.currentAgent?.capabilities || []
  return caps.includes('voice')
})

const voiceStatus = ref('idle')
const voiceRecording = ref(false)
const voiceInterimTranscript = ref('')
const voiceAudioLevel = ref(0)
let voiceWs = null
const currentStreamingMsgIndex = ref(-1)

const voiceStatusText = computed(() => {
  const texts = {
    idle: '点击麦克风开始对话',
    connecting: '连接中...',
    listening: '正在听您说...',
    processing: '思考中...',
    speaking: '正在回复...',
    error: '连接出错'
  }
  return texts[voiceStatus.value] || ''
})

const {
  isPlaying: isVoicePlaying,
  playAudioChunk,
  stop: stopVoiceAudio,
  reset: resetVoiceAudio
} = useAudioPlayer()

const {
  startCapture,
  stopCapture
} = useAudioCapture({
  onAudioChunk: (chunk) => {
    if (voiceWs) sendAudio(voiceWs, chunk)
  },
  onAudioLevel: (level) => {
    voiceAudioLevel.value = level
  },
  vadEnabled: false
})

function handleVoiceMessage(msg) {
  switch (msg.type) {
    case 'status':
      if (!voiceRecording.value && msg.status === 'listening') break
      voiceStatus.value = msg.status
      if (msg.status === 'idle' && voiceRecording.value) {
        sendControl(voiceWs, 'start')
        voiceStatus.value = 'listening'
      }
      if (msg.status === 'listening' && currentStreamingMsgIndex.value === -2) {
        currentStreamingMsgIndex.value = -1
      }
      break
    case 'transcription':
      if (msg.text && isVoicePlaying.value) {
        stopVoiceAudio()
        resetVoiceAudio()
        currentStreamingMsgIndex.value = -2
        if (voiceWs) sendControl(voiceWs, 'interrupt')
        voiceInterimTranscript.value = ''
        voiceStatus.value = 'listening'
      }
      if (msg.is_final) {
        if (msg.text) {
          chatStore.addMessage({ role: 'user', content: msg.text })
          saveVoiceMessage(chatStore.currentThreadId, { role: 'user', content: msg.text }).catch(() => {})
          scrollToBottom()
        }
        voiceInterimTranscript.value = ''
        currentStreamingMsgIndex.value = -1
      } else {
        voiceInterimTranscript.value = msg.text || ''
      }
      break
    case 'response':
      if (msg.text && currentStreamingMsgIndex.value !== -2) {
        if (currentStreamingMsgIndex.value === -1) {
          chatStore.addMessage({ role: 'assistant', content: msg.text })
          currentStreamingMsgIndex.value = chatStore.messages.length - 1
        } else {
          chatStore.updateLastAssistantMessage(
            chatStore.messages[currentStreamingMsgIndex.value].content + msg.text
          )
        }
        scrollToBottom()
      }
      break
    case 'response_end':
      if (currentStreamingMsgIndex.value >= 0) {
        const completeMsg = chatStore.messages[currentStreamingMsgIndex.value]
        if (completeMsg) {
          saveVoiceMessage(chatStore.currentThreadId, completeMsg).catch(() => {})
        }
      }
      currentStreamingMsgIndex.value = -1
      break
    case 'audio':
      if (msg.audio_data && currentStreamingMsgIndex.value !== -2) {
        playAudioChunk(msg.audio_data)
        voiceStatus.value = 'speaking'
      }
      break
    case 'audio_end':
      break
    case 'error':
      console.error('Voice error:', msg.error)
      voiceStatus.value = 'error'
      currentStreamingMsgIndex.value = -1
      break
  }
}

function connectVoiceWebSocket() {
  if (voiceWs) return
  voiceStatus.value = 'connecting'
  voiceWs = createVoiceWebSocket(agentStore.selectedAgentId, {
    onMessage: handleVoiceMessage,
    onClose: () => {
      voiceWs = null
      if (voiceRecording.value) stopVoiceRecording()
    },
    onError: () => {
      voiceStatus.value = 'error'
    }
  })
}

async function startVoiceRecording() {
  stopVoiceAudio()
  resetVoiceAudio()
  currentStreamingMsgIndex.value = -1

  if (!chatStore.currentThreadId) {
    await chatStore.createThread(agentStore.selectedAgentId)
    if (!chatStore.currentThreadId) return
  }

  connectVoiceWebSocket()

  const checkAndStart = () => {
    if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
      sendControl(voiceWs, 'start')
      startCapture()
      voiceRecording.value = true
    } else if (voiceWs) {
      setTimeout(checkAndStart, 100)
    }
  }
  checkAndStart()
}

function stopVoiceRecording() {
  stopCapture()
  stopVoiceAudio()
  resetVoiceAudio()
  currentStreamingMsgIndex.value = -2
  voiceRecording.value = false
  voiceInterimTranscript.value = ''
  if (voiceWs) {
    voiceWs.close()
    voiceWs = null
  }
  voiceStatus.value = 'idle'
}

function toggleVoiceRecording() {
  if (voiceRecording.value) {
    stopVoiceRecording()
  } else {
    startVoiceRecording()
  }
}

// 初始化
onMounted(async () => {
  if (!agentStore.isInitialized) {
    await agentStore.initialize()
  }
  if (agentStore.selectedAgentId) {
    await chatStore.loadThreads(agentStore.selectedAgentId)
  }
})

// 切换智能体时重新加载会话列表
watch(() => agentStore.selectedAgentId, async (newId) => {
  if (voiceRecording.value) stopVoiceRecording()
  if (newId) {
    chatStore.reset()
    await chatStore.loadThreads(newId)
  }
})

// 切换会话时加载历史
watch(() => chatStore.currentThreadId, async (threadId) => {
  if (threadId && agentStore.selectedAgentId) {
    await chatStore.loadHistory(agentStore.selectedAgentId, threadId)
    scrollToBottom()
  }
})

// 新消息时自动滚动
watch(() => chatStore.messages.length, () => {
  nextTick(scrollToBottom)
})

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

function autoResize(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 160) + 'px'
}

async function selectAgent(agentId) {
  agentStore.selectAgent(agentId)
  showAgentModal.value = false
}

async function handleNewChat() {
  if (!agentStore.selectedAgentId) return
  await chatStore.createThread(agentStore.selectedAgentId)
}

function switchThread(threadId) {
  chatStore.selectThread(threadId)
}

async function sendMessage(text) {
  const content = text || userInput.value.trim()
  if (!content || chatStore.isProcessing) return

  const agentId = agentStore.selectedAgentId
  if (!agentId) return

  userInput.value = ''
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
  }

  // 确保有会话
  let threadId = chatStore.currentThreadId
  if (!threadId) {
    const result = await chatStore.createThread(agentId)
    threadId = result?.id
    if (!threadId) return
  }

  // 添加用户消息
  chatStore.addMessage({ role: 'user', content })
  chatStore.isProcessing = true

  // 添加空的助手消息
  chatStore.addMessage({ role: 'assistant', content: '' })

  try {
    const response = await agentApi.sendAgentMessage(agentId, {
      query: content,
      config: {
        thread_id: threadId
      }
    })

    if (!response.body) throw new Error('无响应体')

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let assistantContent = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed) continue
        try {
          const chunk = JSON.parse(trimmed)
          if (chunk.status === 'error') {
            chatStore.updateLastAssistantMessage('⚠️ ' + (chunk.error_message || '请求失败'))
            break
          }
          if (chunk.status === 'loading' && chunk.response) {
            const msg = chunk.msg || {}
            const msgType = (msg.type || '').toLowerCase()
            // 跳过 tool 类型消息，只显示 AI 文本
            if (msgType !== 'tool' && !msgType.includes('tool')) {
              assistantContent += chunk.response
              chatStore.updateLastAssistantMessage(assistantContent)
              scrollToBottom()
            }
          }
        } catch {}
      }
    }

    // 处理剩余 buffer
    if (buffer.trim()) {
      try {
        const chunk = JSON.parse(buffer.trim())
        if (chunk.status === 'loading' && chunk.response) {
          const msg = chunk.msg || {}
          const msgType = (msg.type || '').toLowerCase()
          if (msgType !== 'tool' && !msgType.includes('tool')) {
            assistantContent += chunk.response
            chatStore.updateLastAssistantMessage(assistantContent)
          }
        }
      } catch {}
    }

    // 刷新会话列表
    await chatStore.loadThreads(agentId)
  } catch (error) {
    console.error('发送消息失败:', error)
    chatStore.updateLastAssistantMessage('⚠️ 发送失败: ' + error.message)
  } finally {
    chatStore.isProcessing = false
  }
}

function handleSend() {
  sendMessage()
}

function handleLogout() {
  stopVoiceRecording()
  userStore.logout()
  chatStore.reset()
  agentStore.reset()
  router.push('/login')
}

onUnmounted(() => {
  if (voiceWs) voiceWs.close()
  stopCapture()
  stopVoiceAudio()
})
</script>

<style lang="less" scoped>
.chat-view {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

// 侧边栏
.sidebar {
  width: 260px;
  background: var(--gray-50);
  border-right: 1px solid var(--gray-200);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border-bottom: 1px solid var(--gray-200);
}

.agent-selector {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: var(--gray-800);
  transition: background 0.15s;

  &:hover { background: var(--gray-200); }

  .agent-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  color: var(--gray-600);
  cursor: pointer;
  transition: background 0.15s;

  &:hover {
    background: var(--gray-200);
    color: var(--gray-800);
  }
}

.thread-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.thread-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--gray-700);
  transition: background 0.15s;

  &:hover { background: var(--gray-200); }

  &.active {
    background: var(--gray-200);
    color: var(--gray-900);
    font-weight: 500;
  }

  .thread-title {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.thread-empty {
  text-align: center;
  padding: 24px 12px;
  color: var(--gray-400);
  font-size: 13px;
}

.sidebar-footer {
  display: flex;
  gap: 4px;
  padding: 12px;
  border-top: 1px solid var(--gray-200);
}

// 主聊天区
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 16px;
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--gray-400);
  gap: 8px;
}

.empty-state {
  h3 {
    margin: 0;
    font-size: 20px;
    color: var(--gray-800);
  }
  p {
    margin: 0;
    font-size: 14px;
    color: var(--gray-500);
    max-width: 400px;
    text-align: center;
  }
  .empty-icon {
    color: var(--color-primary-500);
    opacity: 0.5;
  }
}

.examples {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
  max-width: 500px;
  justify-content: center;
}

.example-btn {
  padding: 8px 14px;
  border: 1px solid var(--gray-200);
  border-radius: 20px;
  background: var(--gray-0);
  color: var(--gray-700);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: var(--color-primary-500);
    color: var(--color-primary-500);
  }
}

// 输入区
.input-area {
  padding: 12px 20px 16px;
  border-top: 1px solid var(--gray-200);
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-md);
  padding: 8px 12px;
  transition: border-color 0.15s;

  &:focus-within {
    border-color: var(--color-primary-500);
  }

  textarea {
    flex: 1;
    border: none;
    background: transparent;
    outline: none;
    resize: none;
    font-size: 14px;
    line-height: 1.5;
    color: var(--gray-900);
    max-height: 160px;
    font-family: inherit;

    &::placeholder {
      color: var(--gray-400);
    }
  }
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: var(--color-primary-500);
  color: #fff;
  cursor: pointer;
  flex-shrink: 0;
  transition: opacity 0.15s;

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  &:not(:disabled):hover {
    opacity: 0.9;
  }
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// 语音输入区
.voice-input-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.voice-interim {
  font-size: 14px;
  color: var(--gray-500);
  font-style: italic;
  text-align: center;
  max-width: 400px;
  word-break: break-all;
}

.voice-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.voice-status-text {
  font-size: 13px;
  color: var(--gray-500);
}

.voice-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  background: var(--color-primary-500);
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    opacity: 0.9;
  }

  &.recording {
    background: #ef4444;
  }

  &.error {
    background: var(--gray-400);
  }

  .voice-level {
    position: absolute;
    inset: -4px;
    border-radius: 50%;
    border: 2px solid var(--color-primary-300);
    transition: transform 0.1s;
    pointer-events: none;
  }

  &.recording .voice-level {
    border-color: rgba(239, 68, 68, 0.4);
  }
}

// 智能体选择弹窗
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 12px;
}

.agent-card {
  padding: 14px;
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: border-color 0.15s;

  &:hover { border-color: var(--color-primary-500); }

  &.selected {
    border-color: var(--color-primary-500);
    background: var(--color-primary-50);
  }

  .agent-card-name {
    font-size: 15px;
    font-weight: 600;
    color: var(--gray-900);
    margin-bottom: 4px;
  }

  .agent-card-desc {
    font-size: 13px;
    color: var(--gray-500);
    line-height: 1.4;
  }
}
</style>
