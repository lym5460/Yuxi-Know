import { defineStore } from 'pinia'
import { ref } from 'vue'
import { agentApi, threadApi } from '@/apis'

export const useChatStore = defineStore('chat', () => {
  const threads = ref([])
  const currentThreadId = ref(null)
  const messages = ref([])
  const isProcessing = ref(false)
  const isLoadingMessages = ref(false)
  const isCreatingThread = ref(false)
  const activeToolCalls = ref([])
  const abortController = ref(null)
  const agentState = ref(null) // { todos: [], files: {} }

  async function loadThreads(agentId) {
    if (!agentId) return
    try {
      const result = await threadApi.getThreads(agentId)
      threads.value = result || []
    } catch (e) {
      console.error('加载会话列表失败:', e)
    }
  }

  async function createThread(agentId) {
    try {
      isCreatingThread.value = true
      const result = await threadApi.createThread(agentId, '新的对话')
      if (result?.id) {
        currentThreadId.value = result.id
        await loadThreads(agentId)
        messages.value = []
      }
      return result
    } catch (e) {
      console.error('创建会话失败:', e)
    } finally {
      isCreatingThread.value = false
    }
  }

  function selectThread(threadId) {
    // 中止当前流式请求
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
    // 保存进行中的工具调用到当前消息（切换前）
    if (isProcessing.value) {
      saveToolCallsToMessage()
      clearToolCalls()
      isProcessing.value = false
    }
    currentThreadId.value = threadId
    messages.value = []
  }

  function setAbortController(controller) {
    abortController.value = controller
  }

  function abortCurrentStream() {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
    if (isProcessing.value) {
      saveToolCallsToMessage()
      clearToolCalls()
      isProcessing.value = false
    }
  }

  async function loadHistory(agentId, threadId) {
    if (!agentId || !threadId) return
    isLoadingMessages.value = true
    try {
      const result = await agentApi.getAgentHistory(agentId, threadId)
      const history = result?.history || []
      // 后端用 type: human/ai/tool/system，映射为 role: user/assistant
      // 合并连续的 AI 消息（LangGraph 一轮对话会产生多条 AI 消息：tool_calls + 文本回复）
      const filtered = history.filter((m) => m.type === 'human' || m.type === 'ai')
      const merged = []
      for (const m of filtered) {
        const role = m.type === 'human' ? 'user' : 'assistant'
        // 提取 toolCalls
        const toolCalls = m.tool_calls?.length
          ? m.tool_calls.map(tc => ({
              id: tc.id,
              name: tc.name || tc.function?.name,
              args: tc.args || {},
              status: tc.tool_call_result ? 'done' : (tc.status || 'calling'),
              result: tc.tool_call_result?.content || undefined
            }))
          : null
        const prev = merged[merged.length - 1]
        // 连续的 assistant 消息合并为一条
        if (role === 'assistant' && prev?.role === 'assistant') {
          if (toolCalls) prev.toolCalls = [...(prev.toolCalls || []), ...toolCalls]
          if (m.content) prev.content = (prev.content ? prev.content + '\n' : '') + m.content
        } else {
          const msg = { role, content: m.content || '', id: m.id }
          if (toolCalls) msg.toolCalls = toolCalls
          if (m.image_content) msg.imageContent = m.image_content
          merged.push(msg)
        }
      }
      messages.value = merged
    } catch (e) {
      console.error('加载历史消息失败:', e)
    } finally {
      isLoadingMessages.value = false
    }
  }

  function addMessage(msg) {
    messages.value.push(msg)
  }

  function updateLastAssistantMessage(content) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.content = content
    }
  }

  function addToolCall(tc) {
    // 优先用 tool_call_id 去重，同一个工具调用的 args 会从 {} 逐步变为完整对象
    if (tc.id) {
      const existing = activeToolCalls.value.find(t => t.id === tc.id)
      if (existing) {
        // 用更完整的 args 更新
        if (tc.args && Object.keys(tc.args).length > Object.keys(existing.args || {}).length) {
          existing.args = tc.args
        }
        return
      }
    }
    activeToolCalls.value.push({ ...tc })
  }

  function completeToolCall(toolCallId, name, result) {
    // 优先按 tool_call_id 匹配，再按 name 匹配
    let tc = toolCallId
      ? activeToolCalls.value.find(t => t.id === toolCallId && t.status !== 'done')
      : null
    if (!tc && name) {
      tc = activeToolCalls.value.find(t => t.name === name && t.status !== 'done')
    }
    if (tc) {
      tc.status = 'done'
      if (result !== undefined) tc.result = result
    }
  }

  function saveToolCallsToMessage() {
    if (!activeToolCalls.value.length) return
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.toolCalls = activeToolCalls.value.map(tc => ({ ...tc }))
    }
  }

  function clearToolCalls() {
    activeToolCalls.value = []
  }

  function setAgentState(state) {
    agentState.value = state
  }

  function reset() {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
    threads.value = []
    currentThreadId.value = null
    messages.value = []
    isProcessing.value = false
    agentState.value = null
    clearToolCalls()
  }

  return {
    threads,
    currentThreadId,
    messages,
    isProcessing,
    isLoadingMessages,
    isCreatingThread,
    activeToolCalls,
    loadThreads,
    createThread,
    selectThread,
    loadHistory,
    addMessage,
    updateLastAssistantMessage,
    addToolCall,
    completeToolCall,
    saveToolCallsToMessage,
    clearToolCalls,
    agentState,
    setAbortController,
    abortCurrentStream,
    setAgentState,
    reset
  }
})
