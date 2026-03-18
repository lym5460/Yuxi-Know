<template>
  <div class="chat-view">
    <!-- 自定义标题栏 -->
    <TitleBar>
      <template #left>
        <div class="agent-selector" @click="showAgentModal = true">
          <Bot :size="16" />
          <span class="agent-name">{{ agentStore.currentAgentName || '选择智能体' }}</span>
          <ChevronDown :size="12" />
        </div>
        <button class="icon-btn" @click="handleNewChat" title="新对话">
          <Plus :size="16" />
        </button>
        <button class="icon-btn" @click="showConfigDrawer = true" title="智能体配置">
          <SlidersHorizontal :size="16" />
        </button>
        <button class="icon-btn" @click="$router.push('/graph')" title="知识图谱">
          <Waypoints :size="16" />
        </button>
      </template>
    </TitleBar>

    <div class="chat-body">
      <!-- 侧边栏 -->
      <div
        class="sidebar"
        :class="{ collapsed: sidebarMode === 'auto' && !sidebarOpen, overlay: sidebarMode === 'auto' }"
        @mouseenter="sidebarMode === 'auto' && (sidebarOpen = true)"
        @mouseleave="sidebarMode === 'auto' && (sidebarOpen = false)"
      >
        <div class="sidebar-header-row">
          <button class="sidebar-pin-btn" @click="toggleSidebarMode" :title="sidebarMode === 'pinned' ? '切换为自动收起' : '固定侧边栏'">
            <Pin v-if="sidebarMode === 'pinned'" :size="13" />
            <PinOff v-else :size="13" />
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
          <button
            class="thread-delete-btn"
            @click.stop="deleteThread(thread.id)"
            title="删除对话"
          >
            <Trash2 :size="13" />
          </button>
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

      <!-- 侧边栏悬浮触发区域（auto 模式且收起时显示） -->
      <div
        v-if="sidebarMode === 'auto' && !sidebarOpen"
        class="sidebar-trigger"
        @mouseenter="sidebarOpen = true"
      >
        <div class="sidebar-trigger-indicator" />
      </div>

      <!-- 主聊天区 -->
      <div class="chat-main">

      <!-- 语音智能体：数字人 + 浮现消息 -->
      <template v-if="isVoiceAgent">
        <div class="voice-stage">
          <VoiceAvatar :audio-level="voiceAudioLevel" :status="voiceStatus" class="voice-avatar" />
          <FloatingChat :messages="chatStore.messages" :interim="voiceInterimTranscript" class="voice-floating" />
        </div>
        <div class="voice-bar">
          <div class="voice-viz-strip">
            <AudioVisualizer :audio-level="voiceAudioLevel" :active="isVoiceActive" class="viz-canvas" />
          </div>
          <div class="voice-controls">
            <button class="voice-mode-btn" @click="toggleVoiceMode" :title="voiceMode === 'pushToTalk' ? '切换为持续对话' : '切换为按住说话'">
              <Hand v-if="voiceMode === 'pushToTalk'" :size="14" />
              <MousePointerClick v-else :size="14" />
              <span>{{ voiceMode === 'pushToTalk' ? '按住说话' : '持续对话' }}</span>
            </button>
            <button
              class="voice-btn"
              :class="{
                recording: voiceMode === 'continuous' ? voiceRecording : spaceHeld,
                connected: voiceMode === 'pushToTalk' && voiceRecording && !spaceHeld,
                error: voiceStatus === 'error',
                hangup: voiceMode === 'continuous' && voiceRecording
              }"
              @click="voiceMode === 'continuous' ? toggleVoiceRecording() : (voiceRecording ? stopVoiceRecording() : null)"
            >
              <PhoneOff v-if="voiceMode === 'continuous' && voiceRecording" :size="18" />
              <Mic v-else :size="18" />
            </button>
          </div>
        </div>
      </template>

      <!-- 文本智能体：标准消息列表 -->
      <template v-else>
      <div class="chat-content-wrapper">
        <div class="chat-content-main">
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
                :tool-calls="chatStore.isProcessing && i === chatStore.messages.length - 1 && msg.role === 'assistant' ? chatStore.activeToolCalls : (msg.toolCalls || [])"
              />
            </template>
          </div>

          <!-- 文本输入区 -->
          <div class="input-area">
            <!-- 图片预览 & 附件列表 -->
            <div v-if="pendingImage || attachments.length" class="upload-preview">
              <div v-if="pendingImage" class="preview-image-wrap">
                <img :src="`data:${pendingImage.mimeType};base64,${pendingImage.thumbnailContent || pendingImage.imageContent}`" :alt="pendingImage.originalName" />
                <button class="preview-remove" @click="removePendingImage"><X :size="12" /></button>
              </div>
              <div
                v-for="att in attachments"
                :key="att.file_id"
                class="attachment-chip"
              >
                <span class="attachment-name">{{ att.file_name }}</span>
                <span v-if="att.status === 'parsed'" class="attachment-status">已解析</span>
                <button class="attachment-remove" @click="removeAttachment(att.file_id)"><X :size="11" /></button>
              </div>
            </div>
            <div class="input-wrapper">
              <button
                v-if="hasAgentStateContent"
                class="state-toggle-btn"
                :class="{ active: agentPanelOpen }"
                @click="agentPanelOpen = !agentPanelOpen"
                title="查看工作状态"
              >
                <FolderCode :size="16" />
              </button>
              <a-tooltip v-if="supportsFileUpload" title="支持 txt/md/docx/html 格式 ≤ 5MB" placement="top">
                <button class="upload-btn" :disabled="isUploading" @click="handleFileSelect">
                  <Paperclip :size="16" />
                </button>
              </a-tooltip>
              <a-tooltip v-if="supportsFileUpload" title="支持 jpg/jpeg/png/gif ≤ 10MB" placement="top">
                <button class="upload-btn" :disabled="isUploading" @click="handleImageSelect">
                  <ImagePlus :size="16" />
                </button>
              </a-tooltip>
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
                v-if="chatStore.isProcessing"
                class="stop-btn"
                @click="handleStopGeneration"
                title="停止生成"
              >
                <Square :size="14" />
              </button>
              <button
                v-else
                class="send-btn"
                :disabled="!userInput.trim() && !pendingImage"
                @click="handleSend"
              >
                <SendHorizontal :size="18" />
              </button>
            </div>
          </div>
        </div>

        <!-- AgentState 面板 -->
        <AgentStatePanel
          v-if="agentPanelOpen && hasAgentStateContent"
          :agent-state="chatStore.agentState"
          class="agent-state-panel-wrapper"
          @close="agentPanelOpen = false"
          @refresh="refreshAgentState"
        />
      </div>
      </template>
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

    <!-- 智能体配置抽屉 -->
    <AgentConfigDrawer
      :open="showConfigDrawer"
      @close="showConfigDrawer = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import {
  Bot, ChevronDown, Plus, MessageSquare, Settings, LogOut,
  SendHorizontal, LoaderCircle, Mic, MicOff, PhoneOff, Trash2,
  Hand, MousePointerClick, PanelLeftClose, PanelLeftOpen, Pin, PinOff,
  SlidersHorizontal, Square, FolderCode, Paperclip, ImagePlus, X, Waypoints
} from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { useAgentStore } from '@/stores/agent'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import { message } from 'ant-design-vue'
import { open as tauriOpen } from '@tauri-apps/plugin-dialog'
import { readFile } from '@tauri-apps/plugin-fs'
import { agentApi, threadApi, multimodalApi } from '@/apis'
import { createVoiceWebSocket, sendAudio, sendControl, saveVoiceMessage } from '@/apis/voice_api'
import { useAudioCapture } from '@/composables/useAudioCapture'
import { useAudioPlayer } from '@/composables/useAudioPlayer'
import { useVideoWindow } from '@/composables/useTauriIntegration'
import { useServerStore } from '@/stores/server'
import ChatMessage from '@/components/ChatMessage.vue'
import TitleBar from '@/components/TitleBar.vue'
import AudioVisualizer from '@/components/AudioVisualizer.vue'
import VoiceAvatar from '@/components/VoiceAvatar.vue'
import FloatingChat from '@/components/FloatingChat.vue'
import AgentConfigDrawer from '@/components/AgentConfigDrawer.vue'
import AgentStatePanel from '@/components/AgentStatePanel.vue'

const router = useRouter()
const agentStore = useAgentStore()
const chatStore = useChatStore()
const userStore = useUserStore()
const serverStore = useServerStore()
const { openVideoWindow, closeVideoWindow, sendMediaCommand } = useVideoWindow()

const userInput = ref('')
const showAgentModal = ref(false)
const showConfigDrawer = ref(false)
const agentPanelOpen = ref(false)
const sidebarMode = ref('pinned') // 'pinned' | 'auto'
const sidebarOpen = ref(true)      // auto 模式下是否展开
const messagesRef = ref(null)
const inputRef = ref(null)

// 文件上传状态
const pendingImage = ref(null) // { imageContent, thumbnailContent, mimeType, originalName }
const attachments = ref([])
const isUploading = ref(false)

const supportsFileUpload = computed(() => {
  const caps = agentStore.currentAgent?.capabilities || []
  return caps.includes('file_upload') && !isVoiceAgent.value
})

const exampleQuestions = computed(() => {
  return agentStore.currentAgent?.examples || []
})

// AgentState 面板：检查是否有内容可显示
const hasAgentStateContent = computed(() => {
  const s = chatStore.agentState
  if (!s) return false
  const todoCount = Array.isArray(s.todos) ? s.todos.length : 0
  const fileCount = s.files ? Object.keys(s.files).length : 0
  return todoCount > 0 || fileCount > 0
})

async function refreshAgentState() {
  const agentId = agentStore.selectedAgentId
  const threadId = chatStore.currentThreadId
  if (!agentId || !threadId) return
  try {
    const res = await agentApi.getAgentState(agentId, threadId)
    chatStore.setAgentState(res?.agent_state || null)
  } catch {}
}

async function fetchAgentState() {
  const agentId = agentStore.selectedAgentId
  const threadId = chatStore.currentThreadId
  if (!agentId || !threadId) return
  try {
    const res = await agentApi.getAgentState(agentId, threadId)
    chatStore.setAgentState(res?.agent_state || null)
    // 有内容时自动展开面板
    if (res?.agent_state) {
      const todos = res.agent_state.todos || []
      const files = res.agent_state.files || {}
      if (todos.length > 0 || Object.keys(files).length > 0) {
        agentPanelOpen.value = true
      }
    }
  } catch {
    chatStore.setAgentState(null)
  }
}

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

// 音频可视化
const isVoiceActive = computed(() => {
  return voiceMode.value === 'continuous' ? voiceRecording.value : spaceHeld.value
})
const currentStreamingMsgIndex = ref(-1)

const voiceMode = ref('continuous') // 'pushToTalk' | 'continuous'

const voiceStatusText = computed(() => {
  if (voiceStatus.value === 'idle') {
    return voiceMode.value === 'pushToTalk' ? '按住空格说话' : '点击麦克风开始对话'
  }
  const texts = {
    connecting: '连接中...',
    listening: '正在听您说...',
    processing: '思考中...',
    speaking: '正在回复...',
    error: '连接出错'
  }
  return texts[voiceStatus.value] || ''
})

function toggleVoiceMode() {
  if (voiceRecording.value) stopVoiceRecording()
  voiceMode.value = voiceMode.value === 'pushToTalk' ? 'continuous' : 'pushToTalk'
}

const {
  isPlaying: isVoicePlaying,
  playAudioChunk,
  stop: stopVoiceAudio,
  reset: resetVoiceAudio
} = useAudioPlayer()

const {
  startCapture,
  pauseCapture,
  stopCapture,
  error: captureError
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
        // 两种模式都自动重启监听，pushToTalk 仅通过空格控制音频采集
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
          // 如果是第一条消息，用内容自动更新对话标题
          if (chatStore.messages.length === 0) {
            const autoTitle = msg.text.slice(0, 30)
            threadApi.updateThread(chatStore.currentThreadId, autoTitle)
              .then(() => chatStore.loadThreads(agentStore.selectedAgentId))
              .catch(() => {})
          }
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
    case 'media_command': {
      const data = msg.data
      if (!data) break
      if (data.action === 'stop') {
        closeVideoWindow()
        break
      }
      if (!data.media_url || !data.media_type) break
      const mediaUrl = data.media_url.startsWith('/') ? serverStore.resolveUrl(data.media_url) : data.media_url
      openVideoWindow().then(() => {
        setTimeout(() => {
          sendMediaCommand({
            action: 'play',
            media_url: mediaUrl,
            media_type: data.media_type,
            start_time: data.start_time || 0,
            media_name: data.description || ''
          })
        }, 500)
      })
      break
    }
    case 'error':
      console.error('Voice error:', msg.error)
      currentStreamingMsgIndex.value = -1
      if (voiceMode.value === 'pushToTalk' && voiceRecording.value) {
        // pushToTalk: 静默重置连接，下次按空格重新建连
        stopVoiceRecording()
      } else {
        voiceStatus.value = 'error'
      }
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
  if (sidebarMode.value === 'auto') sidebarOpen.value = false
  stopVoiceAudio()
  resetVoiceAudio()
  currentStreamingMsgIndex.value = -1

  if (!chatStore.currentThreadId) {
    await chatStore.createThread(agentStore.selectedAgentId)
    if (!chatStore.currentThreadId) return
  }

  connectVoiceWebSocket()

  const checkAndStart = async () => {
    if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
      sendControl(voiceWs, 'start')
      await startCapture()
      if (captureError.value) {
        console.error('麦克风获取失败:', captureError.value)
        voiceStatus.value = 'error'
        voiceWs.close()
        voiceWs = null
        return
      }
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
    voiceWs.onclose = null
    voiceWs.onerror = null
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

// 全局按住空格说话（仅控制音频捕获，不影响 WebSocket 连接）
const spaceHeld = ref(false)

function handleKeyDown(e) {
  if (e.code !== 'Space' || e.repeat) return
  const tag = document.activeElement?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || document.activeElement?.isContentEditable) return
  if (voiceMode.value !== 'pushToTalk') return
  if (!isVoiceAgent.value || chatStore.isProcessing) return
  e.preventDefault()
  spaceHeld.value = true
  if (!voiceRecording.value) {
    startVoiceRecording()
  } else {
    // 恢复音频捕获（后端会话通过 auto-restart 保持活跃）
    startCapture()
  }
}

function handleKeyUp(e) {
  if (e.code !== 'Space' || !spaceHeld.value) return
  e.preventDefault()
  spaceHeld.value = false
  if (voiceRecording.value) {
    pauseCapture()
  }
}

// 初始化
onMounted(async () => {
  document.addEventListener('keydown', handleKeyDown)
  document.addEventListener('keyup', handleKeyUp)
  if (!agentStore.isInitialized) {
    await agentStore.initialize()
  }
  if (agentStore.selectedAgentId) {
    await chatStore.loadThreads(agentStore.selectedAgentId)
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeyDown)
  document.removeEventListener('keyup', handleKeyUp)
})

// 切换智能体时重新加载会话列表
watch(() => agentStore.selectedAgentId, async (newId) => {
  if (voiceRecording.value) stopVoiceRecording()
  if (newId) {
    chatStore.reset()
    await chatStore.loadThreads(newId)
    // 自动选中最新的对话
    if (chatStore.threads.length) {
      chatStore.selectThread(chatStore.threads[0].id)
    }
  }
})

// 语音智能体自动收起侧边栏，非语音智能体固定显示
watch(isVoiceAgent, (val) => {
  if (val) {
    sidebarMode.value = 'auto'
    sidebarOpen.value = false
  } else {
    sidebarMode.value = 'pinned'
    sidebarOpen.value = true
  }
}, { immediate: true })

function toggleSidebarMode() {
  if (sidebarMode.value === 'pinned') {
    sidebarMode.value = 'auto'
    sidebarOpen.value = false
  } else {
    sidebarMode.value = 'pinned'
    sidebarOpen.value = true
  }
}

// 切换会话时加载历史，并断开旧的语音连接
watch(() => chatStore.currentThreadId, async (threadId) => {
  if (voiceRecording.value) stopVoiceRecording()
  // 新建 thread 时跳过 loadHistory，消息由 sendMessage / 语音回调管理
  if (chatStore.isCreatingThread) return
  chatStore.setAgentState(null)
  agentPanelOpen.value = false
  pendingImage.value = null
  attachments.value = []
  if (threadId && agentStore.selectedAgentId) {
    await chatStore.loadHistory(agentStore.selectedAgentId, threadId)
    scrollToBottom()
    fetchAgentState()
    loadAttachments(threadId)
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
  // 当前对话为空时不重复创建
  if (chatStore.currentThreadId && chatStore.messages.length === 0) return
  await chatStore.createThread(agentStore.selectedAgentId)
}

function switchThread(threadId) {
  if (threadId === chatStore.currentThreadId) return
  chatStore.selectThread(threadId)
}

async function deleteThread(threadId) {
  if (!threadId) return
  const wasActive = chatStore.currentThreadId === threadId
  try {
    await threadApi.deleteThread(threadId)
    await chatStore.loadThreads(agentStore.selectedAgentId)
    if (wasActive) {
      if (chatStore.threads.length) {
        chatStore.selectThread(chatStore.threads[0].id)
      } else {
        await chatStore.createThread(agentStore.selectedAgentId)
      }
    }
  } catch (e) {
    console.error('删除对话失败:', e)
  }
}

// 文件上传相关
async function loadAttachments(threadId) {
  if (!threadId) return
  try {
    const result = await threadApi.getThreadAttachments(threadId)
    attachments.value = result?.attachments || []
  } catch {
    attachments.value = []
  }
}

const MIME_MAP = { jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png', gif: 'image/gif' }

async function handleImageSelect() {
  const allowedImageExts = ['jpg', 'jpeg', 'png', 'gif']
  const selected = await tauriOpen({
    multiple: false,
    title: '选择图片',
    filters: [{ name: '图片', extensions: allowedImageExts }]
  })
  if (!selected) return
  const filePath = String(Array.isArray(selected) ? selected[0] : selected)
  const ext = filePath.split('.').pop()?.toLowerCase()
  if (!ext || !allowedImageExts.includes(ext)) {
    message.error(`不支持的图片格式，仅支持 ${allowedImageExts.join(', ')}`)
    return
  }

  isUploading.value = true
  const hide = message.loading('图片上传中...', 0)
  try {
    const content = await readFile(filePath)
    if (content.byteLength > 10 * 1024 * 1024) {
      message.error('图片文件过大，请选择小于 10MB 的图片')
      return
    }
    const fileName = filePath.split('/').pop()
    const ext = fileName.split('.').pop().toLowerCase()
    const file = new File([content], fileName, { type: MIME_MAP[ext] || 'image/jpeg' })

    const result = await multimodalApi.uploadImage(file)
    if (result?.image_content) {
      pendingImage.value = {
        imageContent: result.image_content,
        thumbnailContent: result.thumbnail_content,
        mimeType: result.mime_type,
        originalName: fileName
      }
      message.success('图片上传成功')
    }
  } catch (err) {
    message.error('图片上传失败: ' + (err.message || '未知错误'))
  } finally {
    hide()
    isUploading.value = false
  }
}

async function handleFileSelect() {
  const allowedFileExts = ['txt', 'md', 'docx', 'html', 'htm']
  const selected = await tauriOpen({
    multiple: true,
    title: '选择附件',
    filters: [{ name: '文档', extensions: allowedFileExts }]
  })
  if (!selected) return
  const rawPaths = Array.isArray(selected) ? selected : [selected]
  // 过滤不支持的文件类型
  const paths = rawPaths.filter(p => {
    const ext = String(p).split('.').pop()?.toLowerCase()
    if (!ext || !allowedFileExts.includes(ext)) {
      message.error(`不支持的文件类型：${String(p).split('/').pop()}，仅支持 ${allowedFileExts.join(', ')}`)
      return false
    }
    return true
  })
  if (!paths.length) return

  const agentId = agentStore.selectedAgentId
  if (!agentId) return

  // 确保有 thread
  if (!chatStore.currentThreadId) {
    await chatStore.createThread(agentId)
    if (!chatStore.currentThreadId) return
  }
  const threadId = chatStore.currentThreadId

  isUploading.value = true
  const hide = message.loading('附件上传中...', 0)
  let successCount = 0
  try {
    for (const filePath of paths) {
      const content = await readFile(String(filePath))
      if (content.byteLength > 5 * 1024 * 1024) {
        message.error(`文件 ${String(filePath).split('/').pop()} 过大，单个附件不超过 5MB`)
        continue
      }
      const fileName = String(filePath).split('/').pop()
      const file = new File([content], fileName)
      await threadApi.uploadThreadAttachment(threadId, file)
      successCount++
    }
    await loadAttachments(threadId)
    if (successCount > 0) {
      message.success(`${successCount} 个附件上传成功`)
    }
  } catch (err) {
    message.error('附件上传失败: ' + (err.message || '未知错误'))
  } finally {
    hide()
    isUploading.value = false
  }
}

function removePendingImage() {
  pendingImage.value = null
}

async function removeAttachment(fileId) {
  const threadId = chatStore.currentThreadId
  if (!threadId || !fileId) return
  try {
    await threadApi.deleteThreadAttachment(threadId, fileId)
    attachments.value = attachments.value.filter(a => a.file_id !== fileId)
  } catch (err) {
    console.error('删除附件失败:', err)
  }
}

async function sendMessage(text) {
  const content = text || userInput.value.trim()
  if (!content && !pendingImage.value) return
  if (chatStore.isProcessing) return

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

  // 如果是第一条消息，用内容自动更新对话标题
  if (chatStore.messages.length === 0) {
    const autoTitle = content.replace(/\s+/g, ' ').trim().slice(0, 30)
    if (autoTitle) {
      const thread = chatStore.threads.find(t => t.id === threadId)
      if (thread) thread.title = autoTitle
      threadApi.updateThread(threadId, autoTitle).catch(() => {})
    }
  }

  // 添加用户消息
  const userMsg = { role: 'user', content }
  if (pendingImage.value) {
    userMsg.imageContent = pendingImage.value.imageContent
  }
  chatStore.addMessage(userMsg)
  chatStore.isProcessing = true
  chatStore.clearToolCalls()

  // 添加空的助手消息
  chatStore.addMessage({ role: 'assistant', content: '' })

  // 创建 AbortController 用于切换对话时中止流
  const controller = new AbortController()
  chatStore.setAbortController(controller)
  const targetThreadId = threadId

  try {
    const requestData = {
      query: content,
      config: {
        thread_id: threadId
      }
    }
    if (pendingImage.value) {
      requestData.image_content = pendingImage.value.imageContent
    }
    pendingImage.value = null

    const response = await agentApi.sendAgentMessage(agentId, requestData, { signal: controller.signal })

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
          if (chunk.status === 'finished') {
            break
          }
          if (chunk.status === 'agent_state' && chunk.agent_state) {
            chatStore.setAgentState(chunk.agent_state)
            const todos = chunk.agent_state.todos || []
            const files = chunk.agent_state.files || {}
            if (todos.length > 0 || Object.keys(files).length > 0) {
              agentPanelOpen.value = true
            }
          }
          if (chunk.status === 'loading') {
            const msg = chunk.msg || {}
            const msgType = (msg.type || '').toLowerCase()

            // 提取 tool call 信息（完整 tool_calls 或增量 tool_call_chunks）
            if (msg.tool_calls?.length) {
              for (const tc of msg.tool_calls) {
                const name = tc.name || tc.function?.name
                if (!name) continue
                let args = tc.args || tc.function?.arguments
                if (typeof args === 'string') { try { args = JSON.parse(args) } catch { args = null } }
                if (args) {
                  chatStore.addToolCall({ id: tc.id, name, args, status: 'calling' })
                }
              }
              scrollToBottom()
            } else if (msg.tool_call_chunks?.length) {
              // 处理增量 tool_call_chunks，提取名称以尽早显示
              for (const tc of msg.tool_call_chunks) {
                const name = tc.name
                if (!name) continue
                chatStore.addToolCall({ id: tc.id, name, args: {}, status: 'calling' })
              }
              scrollToBottom()
            }

            // 标记 tool 执行完成，附带结果
            if (msgType === 'tool') {
              const result = msg.content || chunk.response || ''
              chatStore.completeToolCall(msg.tool_call_id, msg.name, result)
              scrollToBottom()
            }

            // AI 文本
            if (chunk.response && msgType !== 'tool' && !msgType.includes('tool')) {
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
    if (error.name === 'AbortError') return
    console.error('发送消息失败:', error)
    if (chatStore.currentThreadId === targetThreadId) {
      chatStore.updateLastAssistantMessage('⚠️ 发送失败: ' + error.message)
    }
  } finally {
    // 只有当线程未切换时才执行清理（切换时由 selectThread 处理）
    if (chatStore.currentThreadId === targetThreadId) {
      chatStore.saveToolCallsToMessage()
      chatStore.isProcessing = false
      chatStore.clearToolCalls()
    }
    chatStore.setAbortController(null)
  }
}

function handleStopGeneration() {
  chatStore.abortCurrentStream()
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
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: var(--gray-0);
}

.chat-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  position: relative;
}

// 侧边栏
.sidebar {
  width: 260px;
  background: var(--gray-50);
  border-right: 1px solid var(--glass-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: relative;
  transition: width 0.25s ease, transform 0.25s ease;
  overflow: hidden;
  z-index: 20;

  // overlay 模式：绝对定位不占空间
  &.overlay {
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    box-shadow: 4px 0 16px rgba(0, 0, 0, 0.3);
  }

  &.collapsed {
    width: 0;
    border-right: none;
    box-shadow: none;

    .thread-list, .sidebar-footer, .sidebar-header-row {
      opacity: 0;
      pointer-events: none;
    }

    &::after { display: none; }
  }

  &::after {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 1px;
    height: 100%;
    background: linear-gradient(180deg, transparent, rgba(0, 212, 255, 0.15), transparent);
    pointer-events: none;
  }
}

.sidebar-header-row {
  display: flex;
  justify-content: flex-end;
  padding: 6px 8px 0;
  flex-shrink: 0;
}

.sidebar-pin-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: var(--radius-sm);
  border: none;
  background: transparent;
  color: var(--gray-500);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    color: var(--color-primary-500);
    background: rgba(0, 212, 255, 0.08);
  }
}

// 侧边栏悬浮触发区域
.sidebar-trigger {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 24px;
  z-index: 15;
  cursor: pointer;
  display: flex;
  align-items: center;

  .sidebar-trigger-indicator {
    width: 3px;
    height: 48px;
    margin-left: 4px;
    border-radius: 3px;
    background: rgba(0, 212, 255, 0.15);
    transition: all 0.25s;
  }

  &:hover .sidebar-trigger-indicator {
    height: 64px;
    background: rgba(0, 212, 255, 0.5);
    box-shadow: 0 0 8px rgba(0, 212, 255, 0.3);
  }
}

.agent-selector {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-primary-500);
  transition: all 0.2s;
  border: 1px solid transparent;

  &:hover {
    background: rgba(0, 212, 255, 0.08);
    border-color: var(--glass-border);
  }

  .agent-name {
    max-width: 140px;
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
  border: 1px solid transparent;
  background: transparent;
  color: var(--gray-500);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: rgba(0, 212, 255, 0.08);
    color: var(--color-primary-500);
    border-color: var(--glass-border);
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
  color: var(--gray-600);
  transition: all 0.2s;
  border: 1px solid transparent;

  &:hover {
    background: rgba(0, 212, 255, 0.06);
    border-color: var(--glass-border);
    color: var(--gray-800);
  }

  &.active {
    background: rgba(0, 212, 255, 0.1);
    border-color: rgba(0, 212, 255, 0.2);
    color: var(--color-primary-500);
    font-weight: 500;
  }

  .thread-delete-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: var(--radius-sm);
    border: none;
    background: transparent;
    color: var(--gray-400);
    cursor: pointer;
    flex-shrink: 0;
    padding: 0;
    opacity: 0;
    transition: color 0.2s, opacity 0.2s;

    &:hover {
      color: var(--color-danger-500);
    }
  }

  &:hover .thread-delete-btn {
    opacity: 1;
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
  border-top: 1px solid var(--glass-border);
}

// 主聊天区
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--gray-0);
}

.chat-content-wrapper {
  flex: 1;
  display: flex;
  min-height: 0;
}

.chat-content-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.agent-state-panel-wrapper {
  width: 300px;
  flex-shrink: 0;
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
    color: var(--color-primary-500);
    text-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
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
    opacity: 0.6;
    filter: drop-shadow(0 0 8px rgba(0, 212, 255, 0.4));
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
  border: 1px solid var(--glass-border);
  border-radius: 20px;
  background: rgba(0, 212, 255, 0.04);
  color: var(--gray-600);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.25s;
  backdrop-filter: blur(8px);

  &:hover {
    border-color: rgba(0, 212, 255, 0.4);
    color: var(--color-primary-500);
    background: rgba(0, 212, 255, 0.08);
    box-shadow: var(--glow-primary-sm);
  }
}

// 输入区
.input-area {
  padding: 12px 20px 16px;
  border-top: 1px solid var(--glass-border);
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 10%;
    right: 10%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.2), transparent);
    pointer-events: none;
  }
}

.input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--gray-100);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  padding: 8px 12px;
  transition: all 0.25s;

  &:focus-within {
    border-color: rgba(0, 212, 255, 0.4);
    box-shadow: var(--glow-primary-sm);
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

.state-toggle-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--gray-400);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s;

  &:hover {
    color: var(--color-primary-500);
    background: rgba(0, 212, 255, 0.08);
  }

  &.active {
    color: var(--color-primary-500);
    background: rgba(0, 212, 255, 0.1);
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
  color: var(--gray-0);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.25s;

  &:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  &:not(:disabled):hover {
    box-shadow: var(--glow-primary);
  }
}

.stop-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 2px solid var(--gray-400);
  background: transparent;
  color: var(--gray-500);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.25s;

  &:hover {
    border-color: var(--color-danger-500, #ef4444);
    color: var(--color-danger-500, #ef4444);
  }
}

// 上传按钮
.upload-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--gray-400);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s;

  &:hover {
    color: var(--color-primary-500);
    background: rgba(0, 212, 255, 0.08);
  }

  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

// 上传预览区
.upload-preview {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 4px 8px;
}

.preview-image-wrap {
  position: relative;
  display: inline-block;

  img {
    display: block;
    max-width: 80px;
    max-height: 80px;
    object-fit: cover;
    border-radius: var(--radius-sm);
    border: 1px solid var(--glass-border);
  }

  .preview-remove {
    position: absolute;
    top: -6px;
    right: -6px;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    border: none;
    background: rgba(0, 0, 0, 0.6);
    color: #fff;
    cursor: pointer;
    z-index: 1;
    transition: background 0.2s;

    &:hover {
      background: rgba(0, 0, 0, 0.85);
    }
  }
}

.attachment-chip {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 12px;
  background: rgba(0, 212, 255, 0.06);
  border: 1px solid var(--glass-border);
  font-size: 12px;
  color: var(--gray-600);

  .attachment-name {
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .attachment-status {
    color: var(--color-primary-500);
    font-size: 11px;
  }

  .attachment-remove {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    border: none;
    background: transparent;
    color: var(--gray-400);
    cursor: pointer;
    padding: 0;
    transition: color 0.2s;

    &:hover {
      color: var(--color-danger-500, #ef4444);
    }
  }
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// 语音模式 - 数字人舞台
.voice-stage {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: radial-gradient(ellipse at center, rgba(0, 20, 40, 0.6) 0%, var(--gray-0) 70%);
}

.voice-avatar {
  width: 100%;
  height: 100%;
}

.voice-floating {
  position: absolute;
  inset: 0;
}

// 语音底栏
.voice-bar {
  flex-shrink: 0;
  border-top: 1px solid var(--glass-border);
  position: relative;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 10%;
    right: 10%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.2), transparent);
    pointer-events: none;
  }
}

.voice-viz-strip {
  width: 100%;
  height: 48px;
  background: rgba(0, 10, 20, 0.5);
}

.viz-canvas {
  width: 100%;
  height: 100%;
}

.voice-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 8px 16px;
}

.voice-mode-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--glass-border);
  background: rgba(0, 212, 255, 0.04);
  color: var(--gray-600);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;

  &:hover {
    border-color: rgba(0, 212, 255, 0.4);
    color: var(--color-primary-500);
    box-shadow: var(--glow-primary-sm);
  }
}

.voice-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 2px solid rgba(0, 212, 255, 0.4);
  background: rgba(0, 212, 255, 0.08);
  color: var(--color-primary-500);
  cursor: pointer;
  transition: all 0.3s;

  &:hover {
    background: rgba(0, 212, 255, 0.15);
    border-color: rgba(0, 212, 255, 0.6);
    box-shadow: 0 0 16px rgba(0, 212, 255, 0.3);
  }

  &.recording {
    background: rgba(0, 212, 255, 0.12);
    border-color: rgba(0, 212, 255, 0.6);
    color: var(--color-primary-500);
    box-shadow: 0 0 12px rgba(0, 212, 255, 0.4);
    animation: pulseGlow 2s ease-in-out infinite;
  }

  &.connected {
    background: rgba(0, 212, 255, 0.06);
    border-color: rgba(0, 212, 255, 0.25);
    color: var(--color-primary-600);
  }

  &.error {
    background: rgba(255, 56, 96, 0.08);
    border-color: rgba(255, 56, 96, 0.3);
    color: var(--gray-400);
  }

  &.hangup {
    background: rgba(239, 68, 68, 0.12);
    border-color: rgba(239, 68, 68, 0.5);
    color: #ef4444;
    box-shadow: 0 0 14px rgba(239, 68, 68, 0.3);
    animation: none;

    &:hover {
      background: rgba(239, 68, 68, 0.22);
      border-color: rgba(239, 68, 68, 0.75);
      box-shadow: 0 0 22px rgba(239, 68, 68, 0.5);
    }
  }
}

@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 0 12px rgba(0, 212, 255, 0.4); }
  50% { box-shadow: 0 0 24px rgba(0, 212, 255, 0.6); }
}

// 智能体选择弹窗
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 12px;
}

.agent-card {
  padding: 14px;
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.25s;
  background: rgba(0, 212, 255, 0.02);

  &:hover {
    border-color: rgba(0, 212, 255, 0.4);
    box-shadow: var(--glow-primary-sm);
  }

  &.selected {
    border-color: var(--color-primary-500);
    background: rgba(0, 212, 255, 0.08);
    box-shadow: var(--glow-primary-sm);
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
