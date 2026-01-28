<template>
  <div class="chat-container">
    <ChatSidebarComponent
      :current-chat-id="currentChatId"
      :chats-list="chatsList"
      :is-sidebar-open="chatUIStore.isSidebarOpen"
      :is-initial-render="localUIState.isInitialRender"
      :single-mode="props.singleMode"
      :agents="agents"
      :selected-agent-id="currentAgentId"
      :is-creating-new-chat="chatUIStore.creatingNewChat"
      @create-chat="createNewChat"
      @select-chat="selectChat"
      @delete-chat="deleteChat"
      @rename-chat="renameChat"
      @toggle-sidebar="toggleSidebar"
      @open-agent-modal="openAgentModal"
      :class="{
        'sidebar-open': chatUIStore.isSidebarOpen,
        'no-transition': localUIState.isInitialRender
      }"
    />
    <div class="chat">
      <div class="chat-header">
        <div class="header__left">
          <slot name="header-left" class="nav-btn"></slot>
          <div
            type="button"
            class="agent-nav-btn"
            v-if="!chatUIStore.isSidebarOpen"
            @click="toggleSidebar"
          >
            <PanelLeftOpen class="nav-btn-icon" size="18" />
          </div>
          <div
            type="button"
            class="agent-nav-btn"
            v-if="!chatUIStore.isSidebarOpen"
            :class="{ 'is-disabled': chatUIStore.creatingNewChat }"
            @click="createNewChat"
          >
            <LoaderCircle
              v-if="chatUIStore.creatingNewChat"
              class="nav-btn-icon loading-icon"
              size="18"
            />
            <MessageCirclePlus v-else class="nav-btn-icon" size="16" />
            <span class="text">新对话</span>
          </div>
          <div v-if="!props.singleMode" class="agent-nav-btn" @click="openAgentModal">
            <LoaderCircle v-if="!currentAgent" class="nav-btn-icon loading-icon" size="18" />
            <Bot v-else :size="18" class="nav-btn-icon" />
            <span class="text hide-text">
              {{ currentAgentName || '选择智能体' }}
            </span>
            <ChevronDown size="16" class="switch-icon" />
          </div>
        </div>
        <div class="header__right">
          <!-- AgentState 显示按钮已移动到输入框底部 -->
          <slot name="header-right"></slot>
        </div>
      </div>

      <div class="chat-content-container">
        <!-- Main Chat Area -->
        <div class="chat-main" ref="chatMainContainer" :class="{ 'voice-mode': supportsVoice }">
          <!-- 语音模式 - 全屏布局 -->
          <template v-if="supportsVoice">
            <div class="voice-full-container">
              <!-- 语音消息区域 -->
              <div class="voice-messages-area" ref="voiceMessagesContainer">
                <!-- 欢迎信息 - 仅在没有消息时显示 -->
                <div v-if="voiceMessages.length === 0" class="voice-welcome">
                  <div class="welcome-icon">🎙️</div>
                  <h2>{{ currentAgentName }}</h2>
                  <p>点击下方麦克风开始语音对话</p>
                </div>
                
                <!-- 消息列表 -->
                <div v-else class="voice-messages-list">
                  <div 
                    v-for="(msg, index) in voiceMessages" 
                    :key="index" 
                    class="voice-message"
                    :class="msg.role"
                  >
                    <div class="voice-message-content">{{ msg.content }}</div>
                  </div>
                </div>
              </div>

              <!-- 底部控制区域 -->
              <div class="voice-controls">
                <!-- 实时转写显示 -->
                <div class="voice-transcription" v-if="voiceTranscription || voiceInterimTranscript">
                  <span class="transcription-text" :class="{ interim: !voiceTranscription && voiceInterimTranscript }">
                    {{ voiceTranscription || voiceInterimTranscript }}
                  </span>
                  <span class="transcription-hint" v-if="!voiceTranscription && voiceInterimTranscript">实时预览</span>
                </div>

                <!-- 音频可视化 -->
                <AudioVisualizer 
                  v-if="voiceRecording" 
                  :audio-level="voiceAudioLevel" 
                  class="voice-visualizer"
                />

                <!-- 状态提示 -->
                <div class="voice-status">
                  <span class="status-dot" :class="voiceStatus"></span>
                  <span class="status-text">{{ voiceStatusText }}</span>
                </div>

                <!-- 麦克风按钮 -->
                <div 
                  class="voice-mic-button"
                  :class="{ recording: voiceRecording, speaking: voiceStatus === 'speaking' }"
                  @click="toggleVoiceRecording"
                >
                  <Mic v-if="!voiceRecording" :size="32" />
                  <MicOff v-else :size="32" />
                </div>

                <!-- 打断按钮 -->
                <a-button
                  v-if="voiceStatus === 'speaking'"
                  class="voice-interrupt-btn"
                  type="text"
                  @click="handleVoiceInterrupt"
                >
                  <StopCircle :size="20" />
                  <span>打断</span>
                </a-button>

                <p class="voice-hint">{{ voiceHintText }}</p>
              </div>
            </div>
          </template>

          <!-- 文本模式 - 原有布局 -->
          <template v-else>
            <!-- 加载状态：加载消息 -->
            <div v-if="isLoadingMessages" class="chat-loading">
              <div class="loading-spinner"></div>
              <span>正在加载消息...</span>
            </div>

            <div v-else-if="!conversations.length" class="chat-examples">
              <div style="margin-bottom: 150px"></div>
              <h1>您好，我是{{ currentAgentName }}！</h1>
            </div>
            <div class="chat-box" ref="messagesContainer">
              <div class="conv-box" v-for="(conv, index) in conversations" :key="index">
                <AgentMessageComponent
                  v-for="(message, msgIndex) in conv.messages"
                  :message="message"
                  :key="msgIndex"
                  :is-processing="
                    isProcessing &&
                    conv.status === 'streaming' &&
                    msgIndex === conv.messages.length - 1
                  "
                  :show-refs="showMsgRefs(message)"
                  @retry="retryMessage(message)"
                >
                </AgentMessageComponent>
                <!-- 显示对话最后一个消息使用的模型 -->
                <RefsComponent
                  v-if="shouldShowRefs(conv)"
                  :message="getLastMessage(conv)"
                  :show-refs="['model', 'copy']"
                  :is-latest-message="false"
                />
              </div>

              <!-- 生成中的加载状态 - 增强条件支持主聊天和resume流程 -->
              <div class="generating-status" v-if="isProcessing && conversations.length > 0">
                <div class="generating-indicator">
                  <div class="loading-dots">
                    <div></div>
                    <div></div>
                    <div></div>
                  </div>
                  <span class="generating-text">正在生成回复...</span>
                </div>
              </div>
            </div>
            <div class="bottom" :class="{ 'start-screen': !conversations.length }">
              <!-- 人工审批弹窗 - 放在输入框上方 -->
              <HumanApprovalModal
                :visible="approvalState.showModal"
                :question="approvalState.question"
                :operation="approvalState.operation"
                @approve="handleApprove"
                @reject="handleReject"
              />

              <!-- 文本模式 UI -->
              <div class="message-input-wrapper">
              <AgentInputArea
                ref="messageInputRef"
                v-model="userInput"
                :is-loading="isProcessing"
                :disabled="!currentAgent"
                :send-button-disabled="(!userInput || !currentAgent) && !isProcessing"
                placeholder="输入问题..."
                :supports-file-upload="supportsFileUpload"
                :supports-voice="false"
                :agent-id="currentAgentId"
                :thread-id="currentChatId"
                :ensure-thread="ensureActiveThread"
                :has-state-content="hasAgentStateContent"
                :is-panel-open="isAgentPanelOpen"
                @send="handleSendOrStop"
                @attachment-changed="handleAgentStateRefresh"
                @toggle-panel="toggleAgentPanel"
              />

              <!-- 示例问题 -->
              <div
                class="example-questions"
                v-if="!conversations.length && exampleQuestions.length > 0"
              >
                <div class="example-chips">
                  <div
                    v-for="question in exampleQuestions"
                    :key="question.id"
                    class="example-chip"
                    @click="handleExampleClick(question.text)"
                  >
                    {{ question.text }}
                  </div>
                </div>
              </div>

              <div class="bottom-actions" v-else>
                <p class="note">请注意辨别内容的可靠性</p>
              </div>
              </div>
            </div>
          </template>
        </div>

        <!-- Agent Panel Area -->

        <transition name="panel-slide">
          <div class="agent-panel-wrapper" v-if="isAgentPanelOpen && hasAgentStateContent">
            <AgentPanel
              :agent-state="currentAgentState"
              :thread-id="currentChatId"
              @refresh="handleAgentStateRefresh"
              @close="toggleAgentPanel"
            />
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, nextTick, computed, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import AgentInputArea from '@/components/AgentInputArea.vue'
import AgentMessageComponent from '@/components/AgentMessageComponent.vue'
import ChatSidebarComponent from '@/components/ChatSidebarComponent.vue'
import RefsComponent from '@/components/RefsComponent.vue'
import { PanelLeftOpen, MessageCirclePlus, LoaderCircle, ChevronDown, Bot, Mic, MicOff, StopCircle } from 'lucide-vue-next'
import { handleChatError, handleValidationError } from '@/utils/errorHandler'
import { ScrollController } from '@/utils/scrollController'
import { AgentValidator } from '@/utils/agentValidator'
import { useAgentStore } from '@/stores/agent'
import { useChatUIStore } from '@/stores/chatUI'
import { storeToRefs } from 'pinia'
import { MessageProcessor } from '@/utils/messageProcessor'
import { agentApi, threadApi } from '@/apis'
import HumanApprovalModal from '@/components/HumanApprovalModal.vue'
import { useApproval } from '@/composables/useApproval'
import { useAgentStreamHandler } from '@/composables/useAgentStreamHandler'
import AgentPanel from '@/components/AgentPanel.vue'
import AudioVisualizer from '@/components/voice/AudioVisualizer.vue'
import { createVoiceWebSocket, sendAudio, sendControl } from '@/apis/voice_api'
import { useAudioCapture } from '@/composables/useAudioCapture'
import { useAudioPlayer } from '@/composables/useAudioPlayer'
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'

// ==================== PROPS & EMITS ====================
const props = defineProps({
  agentId: { type: String, default: '' },
  singleMode: { type: Boolean, default: true }
})
const emit = defineEmits(['open-config', 'open-agent-modal'])

// ==================== STORE MANAGEMENT ====================
const agentStore = useAgentStore()
const chatUIStore = useChatUIStore()
const { agents, selectedAgentId, defaultAgentId, selectedAgentConfigId } = storeToRefs(agentStore)

// ==================== LOCAL CHAT & UI STATE ====================
const userInput = ref('')

// 从智能体元数据获取示例问题
const exampleQuestions = computed(() => {
  const agentId = currentAgentId.value
  let examples = []
  if (agentId && agents.value && agents.value.length > 0) {
    const agent = agents.value.find((a) => a.id === agentId)
    examples = agent ? agent.examples || [] : []
  }
  return examples.map((text, index) => ({
    id: index + 1,
    text: text
  }))
})

// Keep per-thread streaming scratch data in a consistent shape.
const createOnGoingConvState = () => ({
  msgChunks: {},
  currentRequestKey: null,
  currentAssistantKey: null,
  toolCallBuffers: {}
})

// 业务状态（保留在组件本地）
const chatState = reactive({
  currentThreadId: null,
  // 以threadId为键的线程状态
  threadStates: {}
})

// 组件级别的线程和消息状态
const threads = ref([])
const threadMessages = ref({})

// 本地 UI 状态（仅在本组件使用）
const localUIState = reactive({
  isInitialRender: true
})

// Agent Panel State
const isAgentPanelOpen = ref(false)

// ==================== COMPUTED PROPERTIES ====================
const currentAgentId = computed(() => {
  if (props.singleMode) {
    return props.agentId || defaultAgentId.value
  } else {
    return selectedAgentId.value
  }
})

const currentAgentName = computed(() => {
  const agent = currentAgent.value
  return agent ? agent.name : '智能体'
})

const currentAgent = computed(() => {
  if (!currentAgentId.value || !agents.value || !agents.value.length) return null
  return agents.value.find((a) => a.id === currentAgentId.value) || null
})
const chatsList = computed(() => threads.value || [])
const currentChatId = computed(() => chatState.currentThreadId)
const currentThread = computed(() => {
  if (!currentChatId.value) return null
  return threads.value.find((thread) => thread.id === currentChatId.value) || null
})

// 检查当前智能体是否支持文件上传
const supportsFileUpload = computed(() => {
  if (!currentAgent.value) return false
  const capabilities = currentAgent.value.capabilities || []
  return capabilities.includes('file_upload')
})
const supportsTodo = computed(() => {
  if (!currentAgent.value) return false
  const capabilities = currentAgent.value.capabilities || []
  return capabilities.includes('todo')
})

const supportsFiles = computed(() => {
  if (!currentAgent.value) return false
  const capabilities = currentAgent.value.capabilities || []
  return capabilities.includes('files')
})

// 检查当前智能体是否支持语音
const supportsVoice = computed(() => {
  if (!currentAgent.value) return false
  const capabilities = currentAgent.value.capabilities || []
  return capabilities.includes('voice')
})

// AgentState 相关计算属性
const currentAgentState = computed(() => {
  return currentChatId.value ? getThreadState(currentChatId.value)?.agentState || null : null
})

const countFiles = (files) => {
  if (!Array.isArray(files)) return 0
  let c = 0
  for (const item of files) {
    if (item && typeof item === 'object') c += Object.keys(item).length
  }
  return c
}

const hasAgentStateContent = computed(() => {
  const s = currentAgentState.value
  if (!s) return false
  const todoCount = Array.isArray(s.todos) ? s.todos.length : 0
  const fileCount = countFiles(s.files)
  const attachmentCount = Array.isArray(s.attachments) ? s.attachments.length : 0
  return todoCount > 0 || fileCount > 0 || attachmentCount > 0
})

const currentThreadMessages = computed(() => threadMessages.value[currentChatId.value] || [])

// 计算是否显示Refs组件的条件
const shouldShowRefs = computed(() => {
  return (conv) => {
    return (
      getLastMessage(conv) &&
      conv.status !== 'streaming' &&
      !approvalState.showModal &&
      !(
        approvalState.threadId &&
        chatState.currentThreadId === approvalState.threadId &&
        isProcessing.value
      )
    )
  }
})

// 当前线程状态的computed属性
const currentThreadState = computed(() => {
  return getThreadState(currentChatId.value)
})

const onGoingConvMessages = computed(() => {
  const threadState = currentThreadState.value
  if (!threadState || !threadState.onGoingConv) return []

  const msgs = Object.values(threadState.onGoingConv.msgChunks).map(
    MessageProcessor.mergeMessageChunk
  )
  return msgs.length > 0
    ? MessageProcessor.convertToolResultToMessages(msgs).filter((msg) => msg.type !== 'tool')
    : []
})

const historyConversations = computed(() => {
  return MessageProcessor.convertServerHistoryToMessages(currentThreadMessages.value)
})

const conversations = computed(() => {
  const historyConvs = historyConversations.value

  // 如果有进行中的消息且线程状态显示正在流式处理，添加进行中的对话
  if (onGoingConvMessages.value.length > 0) {
    const onGoingConv = {
      messages: onGoingConvMessages.value,
      status: 'streaming'
    }
    return [...historyConvs, onGoingConv]
  }
  return historyConvs
})

const isLoadingMessages = computed(() => chatUIStore.isLoadingMessages)
const isStreaming = computed(() => {
  const threadState = currentThreadState.value
  return threadState ? threadState.isStreaming : false
})
const isProcessing = computed(() => isStreaming.value)

// ==================== SCROLL & RESIZE HANDLING ====================
// Update scroll controller to target .chat-main
const scrollController = new ScrollController('.chat-main')

onMounted(() => {
  nextTick(() => {
    // Update event listener to target .chat-main
    const chatMainContainer = document.querySelector('.chat-main')
    if (chatMainContainer) {
      chatMainContainer.addEventListener('scroll', scrollController.handleScroll, { passive: true })
    }
  })
  setTimeout(() => {
    localUIState.isInitialRender = false
  }, 300)
})

onUnmounted(() => {
  scrollController.cleanup()
  // 清理所有线程状态
  resetOnGoingConv()
  // 清理语音资源
  cleanupVoice()
})

// ==================== THREAD STATE MANAGEMENT ====================
// 获取指定线程的状态，如果不存在则创建
const getThreadState = (threadId) => {
  if (!threadId) return null
  if (!chatState.threadStates[threadId]) {
    chatState.threadStates[threadId] = {
      isStreaming: false,
      streamAbortController: null,
      onGoingConv: createOnGoingConvState(),
      agentState: null // 添加 agentState 字段
    }
  }
  return chatState.threadStates[threadId]
}

// 清理指定线程的状态
const cleanupThreadState = (threadId) => {
  if (!threadId) return
  const threadState = chatState.threadStates[threadId]
  if (threadState) {
    if (threadState.streamAbortController) {
      threadState.streamAbortController.abort()
    }
    delete chatState.threadStates[threadId]
  }
}

// ==================== STREAM HANDLING LOGIC ====================
const resetOnGoingConv = (threadId = null) => {
  console.log(
    `🔄 [RESET] Resetting on going conversation: ${new Date().toLocaleTimeString()}.${new Date().getMilliseconds()}`,
    threadId
  )

  const targetThreadId = threadId || currentChatId.value

  if (targetThreadId) {
    // 清理指定线程的状态
    const threadState = getThreadState(targetThreadId)
    if (threadState) {
      if (threadState.streamAbortController) {
        threadState.streamAbortController.abort()
        threadState.streamAbortController = null
      }

      // 直接重置对话状态
      threadState.onGoingConv = createOnGoingConvState()
    }
  } else {
    // 如果没有当前线程，清理所有线程状态
    Object.keys(chatState.threadStates).forEach((tid) => {
      cleanupThreadState(tid)
    })
  }
}

// ==================== 线程管理方法 ====================
// 获取当前智能体的线程列表
const fetchThreads = async (agentId = null) => {
  const targetAgentId = agentId || currentAgentId.value
  if (!targetAgentId) return

  chatUIStore.isLoadingThreads = true
  try {
    const fetchedThreads = await threadApi.getThreads(targetAgentId)
    threads.value = fetchedThreads || []
  } catch (error) {
    console.error('Failed to fetch threads:', error)
    handleChatError(error, 'fetch')
    throw error
  } finally {
    chatUIStore.isLoadingThreads = false
  }
}

// 创建新线程
const createThread = async (agentId, title = '新的对话') => {
  if (!agentId) return null

  chatState.isCreatingThread = true
  try {
    const thread = await threadApi.createThread(agentId, title)
    if (thread) {
      threads.value.unshift(thread)
      threadMessages.value[thread.id] = []
    }
    return thread
  } catch (error) {
    console.error('Failed to create thread:', error)
    handleChatError(error, 'create')
    throw error
  } finally {
    chatState.isCreatingThread = false
  }
}

// 删除线程
const deleteThread = async (threadId) => {
  if (!threadId) return

  chatState.isDeletingThread = true
  try {
    await threadApi.deleteThread(threadId)
    threads.value = threads.value.filter((thread) => thread.id !== threadId)
    delete threadMessages.value[threadId]

    if (chatState.currentThreadId === threadId) {
      chatState.currentThreadId = null
    }
  } catch (error) {
    console.error('Failed to delete thread:', error)
    handleChatError(error, 'delete')
    throw error
  } finally {
    chatState.isDeletingThread = false
  }
}

// 更新线程标题
const updateThread = async (threadId, title) => {
  if (!threadId || !title) return

  chatState.isRenamingThread = true
  try {
    await threadApi.updateThread(threadId, title)
    const thread = threads.value.find((t) => t.id === threadId)
    if (thread) {
      thread.title = title
    }
  } catch (error) {
    console.error('Failed to update thread:', error)
    handleChatError(error, 'update')
    throw error
  } finally {
    chatState.isRenamingThread = false
  }
}

// 获取线程消息
const fetchThreadMessages = async ({ agentId, threadId, delay = 0 }) => {
  if (!threadId || !agentId) return

  // 如果指定了延迟，等待指定时间（用于确保后端数据库事务提交）
  if (delay > 0) {
    await new Promise((resolve) => setTimeout(resolve, delay))
  }

  try {
    const response = await agentApi.getAgentHistory(agentId, threadId)
    console.log(
      `🔄 [FETCH] Thread messages: ${new Date().toLocaleTimeString()}.${new Date().getMilliseconds()}`,
      response
    )
    threadMessages.value[threadId] = response.history || []
  } catch (error) {
    handleChatError(error, 'load')
    throw error
  }
}

const fetchAgentState = async (agentId, threadId) => {
  if (!agentId || !threadId) return
  try {
    const res = await agentApi.getAgentState(agentId, threadId)
    const ts = getThreadState(threadId)
    if (ts) ts.agentState = res.agent_state || null
  } catch (error) {}
}

const ensureActiveThread = async (title = '新的对话') => {
  if (currentChatId.value) return currentChatId.value
  try {
    const newThread = await createThread(currentAgentId.value, title || '新的对话')
    if (newThread) {
      chatState.currentThreadId = newThread.id
      return newThread.id
    }
  } catch (error) {
    // createThread 已处理错误提示
  }
  return null
}

// ==================== 审批功能管理 ====================
const { approvalState, handleApproval, processApprovalInStream } = useApproval({
  getThreadState,
  resetOnGoingConv,
  fetchThreadMessages
})

const { handleAgentResponse } = useAgentStreamHandler({
  getThreadState,
  processApprovalInStream,
  currentAgentId,
  supportsTodo,
  supportsFiles
})

// 发送消息并处理流式响应
const sendMessage = async ({
  agentId,
  threadId,
  text,
  signal = undefined,
  imageData = undefined
}) => {
  if (!agentId || !threadId || !text) {
    const error = new Error('Missing agent, thread, or message text')
    handleChatError(error, 'send')
    return Promise.reject(error)
  }

  // 如果是新对话，用消息内容作为标题
  if ((threadMessages.value[threadId] || []).length === 0) {
    updateThread(threadId, text)
  }

  const requestData = {
    query: text,
    config: {
      thread_id: threadId,
      ...(selectedAgentConfigId.value ? { agent_config_id: selectedAgentConfigId.value } : {})
    }
  }

  // 如果有图片，添加到请求中
  if (imageData && imageData.imageContent) {
    requestData.image_content = imageData.imageContent
  }

  try {
    return await agentApi.sendAgentMessage(agentId, requestData, signal ? { signal } : undefined)
  } catch (error) {
    handleChatError(error, 'send')
    throw error
  }
}

// ==================== CHAT ACTIONS ====================
// 检查第一个对话是否为空
const isFirstChatEmpty = () => {
  if (threads.value.length === 0) return false
  const firstThread = threads.value[0]
  const firstThreadMessages = threadMessages.value[firstThread.id] || []
  return firstThreadMessages.length === 0
}

// 如果第一个对话为空，直接切换到第一个对话
const switchToFirstChatIfEmpty = async () => {
  if (threads.value.length > 0 && isFirstChatEmpty()) {
    await selectChat(threads.value[0].id)
    return true
  }
  return false
}

const createNewChat = async () => {
  if (
    !AgentValidator.validateAgentId(currentAgentId.value, '创建对话') ||
    chatUIStore.creatingNewChat
  )
    return

  // 如果第一个对话为空，直接切换到第一个对话而不是创建新对话
  if (await switchToFirstChatIfEmpty()) return

  // 只有当当前对话是第一个对话且为空时，才阻止创建新对话
  const currentThreadIndex = threads.value.findIndex((thread) => thread.id === currentChatId.value)
  if (currentChatId.value && conversations.value.length === 0 && currentThreadIndex === 0) return

  chatUIStore.creatingNewChat = true
  try {
    const newThread = await createThread(currentAgentId.value, '新的对话')
    if (newThread) {
      // 中断之前线程的流式输出（如果存在）
      const previousThreadId = chatState.currentThreadId
      if (previousThreadId) {
        const previousThreadState = getThreadState(previousThreadId)
        if (previousThreadState?.isStreaming && previousThreadState.streamAbortController) {
          previousThreadState.streamAbortController.abort()
          previousThreadState.isStreaming = false
          previousThreadState.streamAbortController = null
        }
      }

      chatState.currentThreadId = newThread.id
    }
  } catch (error) {
    handleChatError(error, 'create')
  } finally {
    chatUIStore.creatingNewChat = false
  }
}

const selectChat = async (chatId) => {
  if (
    !AgentValidator.validateAgentIdWithError(
      currentAgentId.value,
      '选择对话',
      handleValidationError
    )
  )
    return

  // 中断之前线程的流式输出（如果存在）
  const previousThreadId = chatState.currentThreadId
  if (previousThreadId && previousThreadId !== chatId) {
    const previousThreadState = getThreadState(previousThreadId)
    if (previousThreadState?.isStreaming && previousThreadState.streamAbortController) {
      previousThreadState.streamAbortController.abort()
      previousThreadState.isStreaming = false
      previousThreadState.streamAbortController = null
    }
  }

  chatState.currentThreadId = chatId
  chatUIStore.isLoadingMessages = true
  try {
    await fetchThreadMessages({ agentId: currentAgentId.value, threadId: chatId })
  } catch (error) {
    handleChatError(error, 'load')
  } finally {
    chatUIStore.isLoadingMessages = false
  }

  await nextTick()
  scrollController.scrollToBottomStaticForce()
  await fetchAgentState(currentAgentId.value, chatId)
}

const deleteChat = async (chatId) => {
  if (
    !AgentValidator.validateAgentIdWithError(
      currentAgentId.value,
      '删除对话',
      handleValidationError
    )
  )
    return
  try {
    await deleteThread(chatId)
    if (chatState.currentThreadId === chatId) {
      chatState.currentThreadId = null
      // 如果删除的是当前对话，自动创建新对话
      await createNewChat()
    } else if (chatsList.value.length > 0) {
      // 如果删除的不是当前对话，选择第一个可用对话
      await selectChat(chatsList.value[0].id)
    }
  } catch (error) {
    handleChatError(error, 'delete')
  }
}

const renameChat = async (data) => {
  let { chatId, title } = data
  if (
    !AgentValidator.validateRenameOperation(
      chatId,
      title,
      currentAgentId.value,
      handleValidationError
    )
  )
    return
  if (title.length > 30) title = title.slice(0, 30)
  try {
    await updateThread(chatId, title)
  } catch (error) {
    handleChatError(error, 'rename')
  }
}

const handleSendMessage = async ({ image } = {}) => {
  console.log('AgentChatComponent: handleSendMessage payload image:', image)
  const text = userInput.value.trim()
  if ((!text && !image) || !currentAgent.value || isProcessing.value) return

  let threadId = currentChatId.value
  if (!threadId) {
    threadId = await ensureActiveThread(text)
    if (!threadId) {
      message.error('创建对话失败，请重试')
      return
    }
  }

  userInput.value = ''

  await nextTick()
  scrollController.scrollToBottom(true)

  const threadState = getThreadState(threadId)
  if (!threadState) return

  threadState.isStreaming = true
  resetOnGoingConv(threadId)
  threadState.streamAbortController = new AbortController()

  try {
    const response = await sendMessage({
      agentId: currentAgentId.value,
      threadId: threadId,
      text: text,
      signal: threadState.streamAbortController?.signal,
      imageData: image
    })

    await handleAgentResponse(response, threadId)
  } catch (error) {
    if (error.name !== 'AbortError') {
      console.error('Stream error:', error)
      handleChatError(error, 'send')
    } else {
      console.warn('[Interrupted] Catch')
    }
    threadState.isStreaming = false
  } finally {
    threadState.streamAbortController = null
    // 异步加载历史记录，保持当前消息显示直到历史记录加载完成
    fetchThreadMessages({ agentId: currentAgentId.value, threadId: threadId, delay: 500 }).finally(
      () => {
        // 历史记录加载完成后，安全地清空当前进行中的对话
        resetOnGoingConv(threadId)
        scrollController.scrollToBottom()
      }
    )
  }
}

// 发送或中断
const handleSendOrStop = async (payload) => {
  const threadId = currentChatId.value
  const threadState = getThreadState(threadId)
  if (isProcessing.value && threadState && threadState.streamAbortController) {
    // 中断生成
    threadState.streamAbortController.abort()

    // 中断后刷新消息历史，确保显示最新的状态
    try {
      await fetchThreadMessages({ agentId: currentAgentId.value, threadId: threadId, delay: 500 })
      message.info('已中断对话生成')
    } catch (error) {
      console.error('刷新消息历史失败:', error)
      message.info('已中断对话生成')
    }
    return
  }
  await handleSendMessage(payload)
}

// ==================== 人工审批处理 ====================
const handleApprovalWithStream = async (approved) => {
  console.log('🔄 [STREAM] Starting resume stream processing')

  const threadId = approvalState.threadId
  if (!threadId) {
    message.error('无效的审批请求')
    approvalState.showModal = false
    return
  }

  const threadState = getThreadState(threadId)
  if (!threadState) {
    message.error('无法找到对应的对话线程')
    approvalState.showModal = false
    return
  }

  try {
    // 使用审批 composable 处理审批
    const response = await handleApproval(
      approved,
      currentAgentId.value,
      selectedAgentConfigId.value
    )

    if (!response) return // 如果 handleApproval 抛出错误，这里不会执行

    console.log('🔄 [STREAM] Processing resume streaming response')

    // 处理流式响应
    await handleAgentResponse(response, threadId, (chunk) => {
      console.log('🔄 [STREAM] Processing chunk:', chunk)
    })

    console.log('🔄 [STREAM] Resume stream processing completed')
  } catch (error) {
    console.error('❌ [STREAM] Resume stream failed:', error)
    if (error.name !== 'AbortError') {
      console.error('Resume approval error:', error)
      // handleChatError 已在 useApproval 中调用
    }
  } finally {
    console.log('🔄 [STREAM] Cleaning up streaming state')
    if (threadState) {
      threadState.isStreaming = false
      threadState.streamAbortController = null
    }

    // 异步加载历史记录，保持当前消息显示直到历史记录加载完成
    fetchThreadMessages({ agentId: currentAgentId.value, threadId: threadId, delay: 500 }).finally(
      () => {
        // 历史记录加载完成后，安全地清空当前进行中的对话
        resetOnGoingConv(threadId)
        scrollController.scrollToBottom()
      }
    )
  }
}

const handleApprove = () => {
  handleApprovalWithStream(true)
}

const handleReject = () => {
  handleApprovalWithStream(false)
}

// 处理示例问题点击
const handleExampleClick = (questionText) => {
  userInput.value = questionText
  nextTick(() => {
    handleSendMessage()
  })
}

const buildExportPayload = () => {
  const agentId = currentAgentId.value
  let agentDescription = ''
  if (agentId && agents.value && agents.value.length > 0) {
    const agent = agents.value.find((a) => a.id === agentId)
    agentDescription = agent ? agent.description || '' : ''
  }

  const payload = {
    chatTitle: currentThread.value?.title || '新对话',
    agentName: currentAgentName.value || currentAgent.value?.name || '智能助手',
    agentDescription: agentDescription || currentAgent.value?.description || '',
    messages: conversations.value ? JSON.parse(JSON.stringify(conversations.value)) : [],
    onGoingMessages: onGoingConvMessages.value
      ? JSON.parse(JSON.stringify(onGoingConvMessages.value))
      : []
  }

  return payload
}

defineExpose({
  getExportPayload: buildExportPayload
})

const toggleSidebar = () => {
  chatUIStore.toggleSidebar()
}
const openAgentModal = () => emit('open-agent-modal')

const handleAgentStateRefresh = async () => {
  if (!currentAgentId.value || !currentChatId.value) return
  await fetchAgentState(currentAgentId.value, currentChatId.value)
}

const toggleAgentPanel = () => {
  isAgentPanelOpen.value = !isAgentPanelOpen.value
}

// 语音模式状态
const voiceStatus = ref('idle')
const voiceTranscription = ref('')
const voiceInterimTranscript = ref('')  // 实时预览文字
const voiceRecording = ref(false)
const voiceAudioLevel = ref(0)
const voiceMessages = ref([])
const voiceMessagesContainer = ref(null)
let voiceWs = null

// 先初始化音频播放器
const { playAudioChunk, stop: stopVoiceAudio, reset: resetVoiceAudio } = useAudioPlayer()

// 初始化浏览器语音识别（用于实时预览）
const { 
  isSupported: speechRecognitionSupported,
  start: startSpeechRecognition,
  stop: stopSpeechRecognition,
  reset: resetSpeechRecognition
} = useSpeechRecognition({
  lang: 'zh-CN',
  continuous: true,
  interimResults: true,
  onResult: (fullText, interim) => {
    // 实时更新预览文字
    voiceInterimTranscript.value = interim || fullText
  },
  onFinalResult: (text) => {
    // 浏览器识别的最终结果（仅用于预览，不作为最终结果）
    console.log('🎤 浏览器识别结果:', text)
  }
})

// 智能打断：当用户开始说话时立即停止 AI
const handleSmartInterrupt = () => {
  console.log('🎤 智能打断触发，当前状态:', voiceStatus.value, '录音状态:', voiceRecording.value)
  
  // 立即停止音频播放
  stopVoiceAudio()
  
  // 设置打断状态，忽略后续的文字和音频
  currentStreamingMsgIndex.value = -2
  
  // 如果 WebSocket 连接存在，发送打断命令
  if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
    sendControl(voiceWs, 'interrupt')
    console.log('📤 已发送打断命令到后端')
  }
  
  // 重置实时预览
  voiceInterimTranscript.value = ''
  resetSpeechRecognition()
  
  // 状态切换到监听
  voiceStatus.value = 'listening'
}

const { startCapture, stopCapture, isSpeaking: voiceIsSpeaking } = useAudioCapture({
  onAudioChunk: (chunk) => {
    if (voiceWs) sendAudio(voiceWs, chunk)
  },
  onAudioLevel: (level) => {
    voiceAudioLevel.value = level
  },
  onSpeechStart: () => {
    console.log('🎤 语音开始，当前状态:', voiceStatus.value)
    // 智能打断：只要用户开始说话，就停止音频播放
    handleSmartInterrupt()
    
    // 启动浏览器语音识别进行实时预览
    if (speechRecognitionSupported.value) {
      resetSpeechRecognition()
      startSpeechRecognition()
    }
  },
  onSpeechEnd: () => {
    console.log('🎤 语音结束，自动触发转录')
    
    // 停止浏览器语音识别
    stopSpeechRecognition()
    
    // VAD 检测到语音结束，自动发送 stop 触发转录
    // 只有在监听状态下才触发转录（避免在打断后立即触发）
    if (voiceRecording.value && voiceWs && voiceStatus.value === 'listening') {
      sendControl(voiceWs, 'stop')
      voiceStatus.value = 'processing'
    }
  },
  // VAD 配置
  vadEnabled: true,
  vadThreshold: 0.08,    // 语音检测阈值（提高以过滤噪音）
  vadSilenceMs: 600,     // 静音 600ms 后认为语音结束
  vadPrefixMs: 200       // 保留语音开始前 200ms 的音频
})

const voiceStatusText = computed(() => {
  const texts = {
    idle: '准备就绪',
    connecting: '连接中...',
    listening: '正在听您说...',
    processing: '思考中...',
    speaking: '正在回复...',
    error: '连接出错'
  }
  return texts[voiceStatus.value] || ''
})

const voiceHintText = computed(() => {
  if (voiceRecording.value) return '说完后会自动识别，点击可结束对话'
  if (voiceStatus.value === 'speaking') return '直接说话即可打断 AI'
  return '点击麦克风开始对话'
})

// 滚动语音消息到底部
function scrollVoiceMessages() {
  nextTick(() => {
    if (voiceMessagesContainer.value) {
      voiceMessagesContainer.value.scrollTop = voiceMessagesContainer.value.scrollHeight
    }
  })
}

// 当前正在流式输出的 AI 消息索引
const currentStreamingMsgIndex = ref(-1)

function handleVoiceMessage(msg) {
  switch (msg.type) {
    case 'status':
      voiceStatus.value = msg.status
      // 当状态变为 idle 且正在录音中，自动重新开始监听
      if (msg.status === 'idle' && voiceRecording.value) {
        sendControl(voiceWs, 'start')
        voiceStatus.value = 'listening'
      }
      // 当状态变为 listening 时，重置音频播放器和打断状态
      if (msg.status === 'listening') {
        resetVoiceAudio()
        // 重置打断状态，允许接收新的消息
        if (currentStreamingMsgIndex.value === -2) {
          currentStreamingMsgIndex.value = -1
        }
      }
      // 当 AI 开始说话时，确保麦克风仍在监听（用于智能打断）
      if (msg.status === 'speaking' && voiceRecording.value) {
        // 麦克风保持开启，继续采集音频用于智能打断检测
        console.log('🔊 AI 开始说话，麦克风保持监听以支持智能打断')
      }
      break
    case 'transcription':
      voiceTranscription.value = msg.text
      if (msg.is_final && msg.text) {
        voiceMessages.value.push({ role: 'user', content: msg.text })
        voiceTranscription.value = ''
        voiceInterimTranscript.value = ''  // 清除实时预览
        resetSpeechRecognition()
        // 重置流式消息索引，准备接收新的 AI 回复
        currentStreamingMsgIndex.value = -1
        // 重置音频播放器，准备播放新的回复
        resetVoiceAudio()
        scrollVoiceMessages()
      }
      break
    case 'response':
      // 流式文本：追加到当前 AI 消息
      // 如果已经被打断（currentStreamingMsgIndex === -2），忽略后续文本
      if (msg.text && currentStreamingMsgIndex.value !== -2) {
        if (currentStreamingMsgIndex.value === -1) {
          // 创建新的 AI 消息
          voiceMessages.value.push({ role: 'assistant', content: msg.text })
          currentStreamingMsgIndex.value = voiceMessages.value.length - 1
        } else {
          // 追加到现有消息
          voiceMessages.value[currentStreamingMsgIndex.value].content += msg.text
        }
        scrollVoiceMessages()
      }
      break
    case 'response_end':
      // 响应结束，重置流式消息索引
      currentStreamingMsgIndex.value = -1
      break
    case 'audio':
      // 只有在正常状态下才播放音频（非打断状态）
      if (msg.audio_data && currentStreamingMsgIndex.value !== -2) {
        playAudioChunk(msg.audio_data)
        voiceStatus.value = 'speaking'
      }
      break
    case 'audio_end':
      // 音频播放结束，如果还在录音模式，切换回监听
      if (voiceRecording.value) {
        voiceStatus.value = 'listening'
        sendControl(voiceWs, 'start')
        // 重置打断状态
        if (currentStreamingMsgIndex.value === -2) {
          currentStreamingMsgIndex.value = -1
        }
      } else {
        voiceStatus.value = 'idle'
      }
      break
    case 'error':
      console.error('Voice error:', msg.error)
      message.error(msg.error || '语音服务出错')
      voiceStatus.value = 'error'
      currentStreamingMsgIndex.value = -1
      break
  }
}

function connectVoiceWebSocket() {
  if (voiceWs) return

  voiceStatus.value = 'connecting'
  voiceWs = createVoiceWebSocket(currentAgentId.value, {
    onMessage: handleVoiceMessage,
    onOpen: () => {
      voiceStatus.value = 'idle'
    },
    onClose: () => {
      voiceWs = null
      if (voiceRecording.value) {
        stopVoiceRecording()
      }
    },
    onError: () => {
      voiceStatus.value = 'error'
      message.error('WebSocket 连接失败')
    }
  })
}

function startVoiceRecording() {
  // 先停止任何正在播放的音频
  stopVoiceAudio()
  // 重置音频播放器状态
  resetVoiceAudio()
  // 重置流式消息索引
  currentStreamingMsgIndex.value = -1
  
  connectVoiceWebSocket()
  
  const checkAndStart = () => {
    if (voiceWs && voiceWs.readyState === WebSocket.OPEN) {
      // 如果当前正在处理或说话，先发送打断命令
      if (voiceStatus.value === 'processing' || voiceStatus.value === 'speaking') {
        sendControl(voiceWs, 'interrupt')
      } else {
        sendControl(voiceWs, 'start')
      }
      startCapture()
      voiceRecording.value = true
      voiceStatus.value = 'listening'
    } else if (voiceWs) {
      setTimeout(checkAndStart, 100)
    }
  }
  checkAndStart()
}

function stopVoiceRecording() {
  // 无条件停止音频播放
  stopVoiceAudio()
  
  // 停止浏览器语音识别
  stopSpeechRecognition()
  
  if (voiceWs) sendControl(voiceWs, 'stop')
  stopCapture()
  voiceRecording.value = false
  voiceTranscription.value = ''
  voiceInterimTranscript.value = ''
  
  if (voiceStatus.value === 'listening') {
    voiceStatus.value = 'processing'
  }
}

function toggleVoiceRecording() {
  if (voiceRecording.value) {
    stopVoiceRecording()
  } else {
    // 如果 AI 正在说话或处理中，先打断
    if (voiceStatus.value === 'speaking' || voiceStatus.value === 'processing') {
      handleVoiceInterrupt()
    }
    startVoiceRecording()
  }
}

function handleVoiceInterrupt() {
  // 立即停止音频播放
  stopVoiceAudio()
  // 设置打断状态，忽略后续的文字和音频
  currentStreamingMsgIndex.value = -2
  // 发送打断命令到后端
  if (voiceWs) sendControl(voiceWs, 'interrupt')
  // 重置音频播放器，准备接收新的音频
  resetVoiceAudio()
  // 如果正在录音，切换到监听状态
  if (voiceRecording.value) {
    voiceStatus.value = 'listening'
  } else {
    voiceStatus.value = 'idle'
  }
}

function cleanupVoice() {
  if (voiceWs) voiceWs.close()
  stopCapture()
  stopVoiceAudio()
}

const handleToggleVoice = (enabled) => {
  if (enabled) {
    message.info('语音模式已开启，请说话...')
  }
}

// ==================== HELPER FUNCTIONS ====================
const getLastMessage = (conv) => {
  if (!conv?.messages?.length) return null
  for (let i = conv.messages.length - 1; i >= 0; i--) {
    if (conv.messages[i].type === 'ai') return conv.messages[i]
  }
  return null
}

const showMsgRefs = (msg) => {
  // 如果正在审批中，不显示 refs
  if (approvalState.showModal) {
    return false
  }

  // 如果当前线程ID与审批线程ID匹配，但审批框已关闭（说明刚刚处理完审批）
  // 且当前有新的流式处理正在进行，则不显示之前被中断的消息的 refs
  if (
    approvalState.threadId &&
    chatState.currentThreadId === approvalState.threadId &&
    !approvalState.showModal &&
    isProcessing
  ) {
    return false
  }

  // 只有真正完成的消息才显示 refs
  if (msg.isLast && msg.status === 'finished') {
    return ['copy']
  }
  return false
}

// ==================== LIFECYCLE & WATCHERS ====================
const loadChatsList = async () => {
  const agentId = currentAgentId.value
  if (!agentId) {
    console.warn('No agent selected, cannot load chats list')
    threads.value = []
    chatState.currentThreadId = null
    return
  }

  try {
    await fetchThreads(agentId)
    if (currentAgentId.value !== agentId) return

    // 如果当前线程不在线程列表中，清空当前线程
    if (
      chatState.currentThreadId &&
      !threads.value.find((t) => t.id === chatState.currentThreadId)
    ) {
      chatState.currentThreadId = null
    }

    // 如果有线程但没有选中任何线程，自动选择第一个
    if (threads.value.length > 0 && !chatState.currentThreadId) {
      await selectChat(threads.value[0].id)
    }
  } catch (error) {
    handleChatError(error, 'load')
  }
}

const initAll = async () => {
  try {
    if (!agentStore.isInitialized) {
      await agentStore.initialize()
    }
  } catch (error) {
    handleChatError(error, 'load')
  }
}

onMounted(async () => {
  await initAll()
  scrollController.enableAutoScroll()
})

watch(
  currentAgentId,
  async (newAgentId, oldAgentId) => {
    if (newAgentId !== oldAgentId) {
      // 清理当前线程状态
      chatState.currentThreadId = null
      threadMessages.value = {}
      // 清理所有线程状态
      resetOnGoingConv()

      if (newAgentId) {
        await loadChatsList()
      } else {
        threads.value = []
      }
    }
  },
  { immediate: true }
)

watch(
  conversations,
  () => {
    if (isProcessing.value) {
      scrollController.scrollToBottom()
    }
  },
  { deep: true, flush: 'post' }
)
</script>

<style lang="less" scoped>
@import '@/assets/css/main.css';
@import '@/assets/css/animations.less';

.chat-container {
  display: flex;
  width: 100%;
  height: 100%;
  position: relative;
}

.chat {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* Changed from overflow-x: hidden to overflow: hidden */
  position: relative;
  box-sizing: border-box;
  transition: all 0.3s ease;

  .chat-header {
    user-select: none;
    // position: sticky; // Not needed if .chat is flex col and header is fixed height item
    // top: 0;
    z-index: 10;
    height: var(--header-height);
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 8px;
    flex-shrink: 0; /* Prevent header from shrinking */

    .header__left,
    .header__right {
      display: flex;
      align-items: center;
    }

    .switch-icon {
      color: var(--gray-500);
      transition: all 0.2s ease;
    }

    .agent-nav-btn:hover .switch-icon {
      color: var(--main-500);
    }
  }
}

.chat-content-container {
  flex: 1;
  display: flex;
  flex-direction: row;
  overflow: hidden;
  position: relative;
  width: 100%;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto; /* Scroll is here now */
  position: relative;
  transition: flex 0.4s ease;

  // 语音模式全屏布局
  &.voice-mode {
    overflow: hidden;
  }
}

// 语音模式样式
.voice-full-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-width: 700px;
  margin: 0 auto;
  width: 100%;
}

.voice-messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  display: flex;
  flex-direction: column;
}

.voice-welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--gray-500);

  .welcome-icon {
    font-size: 48px;
    margin-bottom: 16px;
  }

  h2 {
    font-size: 24px;
    font-weight: 500;
    color: var(--gray-700);
    margin: 0 0 8px 0;
  }

  p {
    font-size: 14px;
    margin: 0;
  }
}

.voice-messages-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.voice-message {
  padding: 12px 16px;
  border-radius: 16px;
  max-width: 80%;
  word-wrap: break-word;
  animation: fadeIn 0.3s ease;

  &.user {
    align-self: flex-end;
    background: var(--main-color);
    color: white;
    border-bottom-right-radius: 4px;
  }

  &.assistant {
    align-self: flex-start;
    background: var(--gray-100);
    color: var(--gray-800);
    border-bottom-left-radius: 4px;
  }
}

.voice-message-content {
  font-size: 15px;
  line-height: 1.6;
}

.voice-controls {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px;
  gap: 16px;
  border-top: 1px solid var(--gray-100);
  background: var(--bg-color);
}

.voice-transcription {
  padding: 10px 16px;
  background: var(--gray-50);
  border-radius: 20px;
  max-width: 90%;
  text-align: center;
  display: flex;
  align-items: center;
  gap: 8px;
}

.transcription-text {
  color: var(--gray-600);
  font-size: 14px;
}

.transcription-text.interim {
  color: var(--gray-400);
  font-style: italic;
}

.transcription-hint {
  font-size: 11px;
  color: var(--gray-400);
  background: var(--gray-100);
  padding: 2px 6px;
  border-radius: 4px;
}

.voice-visualizer {
  height: 40px;
  width: 200px;
}

.voice-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--gray-300);
  transition: all 0.3s;

  &.idle { background: var(--gray-400); }
  &.connecting { background: var(--color-warning); animation: pulse 1s infinite; }
  &.listening { background: var(--color-success); animation: pulse 1s infinite; }
  &.processing { background: var(--color-warning); animation: pulse 0.5s infinite; }
  &.speaking { background: var(--main-color); animation: pulse 1s infinite; }
  &.error { background: var(--color-error); }
}

.status-text {
  font-size: 14px;
  color: var(--gray-600);
}

.voice-mic-button {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--main-color);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px var(--shadow-2);

  &:hover {
    transform: scale(1.05);
    box-shadow: 0 6px 16px var(--shadow-3);
  }

  &:active {
    transform: scale(0.95);
  }

  &.recording {
    background: var(--color-error);
    animation: recording-pulse 1.5s infinite;
  }

  &.speaking {
    background: var(--main-color);
    opacity: 0.7;
    cursor: not-allowed;
  }
}

.voice-interrupt-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--color-error);
  
  &:hover {
    color: var(--color-error);
    background: var(--color-error-bg);
  }
}

.voice-hint {
  font-size: 13px;
  color: var(--gray-400);
  margin: 0;
}

.agent-panel-wrapper {
  flex: 1; /* 1:1 ratio with chat-main */
  height: calc(100% - 32px);
  overflow: hidden;
  z-index: 20;
  margin: 16px;
  margin-left: 0;
  background: var(--gray-0);
  border-radius: 12px;
  box-shadow: 0 4px 20px var(--shadow-1);
  border: 1px solid var(--gray-200);
}

/* Workbench transition animations */
.panel-slide-enter-active,
.panel-slide-leave-active {
  transition:
    transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1),
    opacity 0.3s ease,
    flex 0.4s ease;
}

.panel-slide-enter-from,
.panel-slide-leave-to {
  transform: translateX(30px) scale(0.98);
  opacity: 0;
  flex: 0 0 0; /* Shrink to zero width during transition */
  margin-left: -16px; /* Compensate for margin during close */
}

.chat-examples {
  padding: 0 50px;
  text-align: center;
  position: absolute;
  bottom: 65%;
  width: 100%;
  z-index: 9;
  animation: slideInUp 0.5s ease-out;

  h1 {
    margin-bottom: 20px;
    font-size: 1.3rem;
    color: var(--gray-1000);
  }

  p {
    font-size: 1.1rem;
    color: var(--gray-700);
  }

  .agent-icons {
    height: 180px;
  }
}

.example-questions {
  margin-top: 16px;
  text-align: center;

  .example-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
  }

  .example-chip {
    padding: 6px 12px;
    background: var(--gray-25);
    // border: 1px solid var(--gray-100);
    border-radius: 16px;
    cursor: pointer;
    font-size: 0.8rem;
    color: var(--gray-700);
    transition: all 0.15s ease;
    white-space: nowrap;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;

    &:hover {
      // background: var(--main-25);
      border-color: var(--main-200);
      color: var(--main-700);
      box-shadow: 0 0px 4px rgba(0, 0, 0, 0.03);
    }

    &:active {
      transform: translateY(0);
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }
  }
}

.chat-loading {
  padding: 0 50px;
  text-align: center;
  position: absolute;
  top: 20%;
  width: 100%;
  z-index: 9;
  animation: slideInUp 0.5s ease-out;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;

  span {
    color: var(--gray-700);
    font-size: 14px;
  }

  .loading-spinner {
    width: 20px;
    height: 20px;
    border: 2px solid var(--gray-200);
    border-top-color: var(--main-color);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

.chat-box {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  flex-grow: 1;
  padding: 1rem;
  display: flex;
  flex-direction: column;
}

.conv-box {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.bottom {
  position: sticky;
  bottom: 0;
  width: 100%;
  margin: 0 auto;
  padding: 4px 1rem 0 1rem;
  background: var(--gray-0);
  z-index: 1000;

  .message-input-wrapper {
    width: 100%;
    max-width: 800px;
    margin: 0 auto;

    .bottom-actions {
      display: flex;
      justify-content: center;
      align-items: center;
    }

    .note {
      font-size: small;
      color: var(--gray-300);
      margin: 4px 0;
      user-select: none;
    }
  }

  &.start-screen {
    position: absolute;
    top: 45%;
    left: 50%;
    transform: translate(-50%, -50%);
    bottom: auto;
    max-width: 800px;
    width: 90%;
    background: transparent;
    padding: 0;
    border-top: none;
    z-index: 100; /* Ensure it's above other elements */
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes recording-pulse {
  0%, 100% { 
    box-shadow: 0 0 0 0 rgba(255, 77, 79, 0.4);
  }
  50% { 
    box-shadow: 0 0 0 20px rgba(255, 77, 79, 0);
  }
}

.loading-dots {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
}

.loading-dots div {
  width: 6px;
  height: 6px;
  background: linear-gradient(135deg, var(--main-color), var(--main-700));
  border-radius: 50%;
  animation: dotPulse 1.4s infinite ease-in-out both;
}

.loading-dots div:nth-child(1) {
  animation-delay: -0.32s;
}

.loading-dots div:nth-child(2) {
  animation-delay: -0.16s;
}

.loading-dots div:nth-child(3) {
  animation-delay: 0s;
}

.generating-status {
  display: flex;
  justify-content: flex-start;
  padding: 1rem 0;
  animation: fadeInUp 0.4s ease-out;
  transition: all 0.2s;
}

.generating-indicator {
  display: flex;
  align-items: center;
  padding: 0.75rem 0rem;

  .generating-text {
    margin-left: 12px;
    font-size: 14px;
    font-weight: 500;
    letter-spacing: 0.025em;
    /* 恢复灰色调：深灰 -> 亮灰(高光) -> 深灰 */
    background: linear-gradient(
      90deg,
      var(--gray-700) 0%,
      var(--gray-700) 40%,
      var(--gray-300) 45%,
      var(--gray-200) 50%,
      var(--gray-300) 55%,
      var(--gray-700) 60%,
      var(--gray-700) 100%
    );
    background-size: 200% auto;
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
    animation: waveFlash 2s linear infinite;
  }
}

@keyframes waveFlash {
  0% {
    background-position: 200% center;
  }
  100% {
    background-position: -200% center;
  }
}

@media (max-width: 1800px) {
  .chat-header {
    background-color: var(--gray-0);
    border-bottom: 1px solid var(--gray-100);
  }
}

@media (max-width: 768px) {
  .chat-header {
    .header__left {
      .text {
        display: none;
      }
    }
  }
}
</style>

<style lang="less">
.agent-nav-btn {
  display: flex;
  gap: 6px;
  padding: 6px 8px;
  height: 32px;
  justify-content: center;
  align-items: center;
  border-radius: 6px;
  color: var(--gray-900);
  cursor: pointer;
  width: auto;
  font-size: 15px;
  transition: background-color 0.3s;
  border: none;
  background: transparent;

  &:hover:not(.is-disabled) {
    background-color: var(--gray-100);
  }

  &.is-disabled {
    cursor: not-allowed;
    opacity: 0.7;
    pointer-events: none;
  }

  .nav-btn-icon {
    height: 18px;
  }

  .loading-icon {
    animation: spin 1s linear infinite;
  }
}

.hide-text {
  display: none;
}

@media (min-width: 769px) {
  .hide-text {
    display: inline;
  }
}

/* AgentState 按钮有内容时的样式 */
.agent-nav-btn.agent-state-btn.has-content:hover:not(.is-disabled) {
  color: var(--main-700);
  background-color: var(--main-20);
}

.agent-nav-btn.agent-state-btn.active {
  color: var(--main-700);
  background-color: var(--main-20);
}
</style>
