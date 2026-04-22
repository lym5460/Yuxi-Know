<script setup>
import { ref, computed, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { useDatabaseStore } from '@/stores/database'
import { useUserStore } from '@/stores/user'
import { videoChatApi } from '@/apis/video_chat_api'
import { mediaApi } from '@/apis/knowledge_api'
import { formatDuration } from '@/utils/file_utils'
import { MdPreview } from 'md-editor-v3'
import { useThemeStore } from '@/stores/theme'
import {
  Send,
  Video,
  FileText,
  Search,
  Loader,
  Plus,
  Play,
  Square,
  Brain,
  Clapperboard,
  RotateCw
} from 'lucide-vue-next'

const databaseStore = useDatabaseStore()
const userStore = useUserStore()
const themeStore = useThemeStore()

// === State ===
const selectedDbId = ref(null)
const videos = ref([])
const selectedVideoNos = ref([])
const messages = ref([])
const inputText = ref('')
const sessionId = ref(String(Date.now()))
const loading = ref(false)
const videosLoading = ref(false)
const messagesContainer = ref(null)
const abortController = ref(null)

// 内嵌播放器
const inlinePlayerRef = ref(null)
const currentVideoUrl = ref('')
const currentVideoInfo = ref(null)
const currentVideoNo = ref('')
const keyframeMarkers = ref([]) // 关键帧标记
const videoPanelVisible = ref(false) // 右侧面板默认收起

// === Computed ===
const memeresDatabases = computed(() => {
  return databaseStore.databases.filter((db) => db.kb_type === 'memeries')
})

const hasSelectedVideos = computed(() => selectedVideoNos.value.length > 0)
const canSend = computed(() => hasSelectedVideos.value && inputText.value.trim() && !loading.value)

// === 预设 Prompt ===
const presetPrompts = [
  {
    label: '视频摘要',
    icon: FileText,
    prompt: '请对这些视频内容进行全面总结，按时间线列出关键事件和重要节点。'
  },
  {
    label: '证据提取',
    icon: Search,
    prompt:
      '请从视频中提取所有可作为证据的关键画面和时间节点，按重要性排序，并说明每个证据的法律意义。'
  }
]

// === 视频播放 ===
async function loadVideoForPlay(videoNo) {
  if (!videoNo || !selectedDbId.value) return
  // 同一个视频：跳到开头重播
  if (videoNo === currentVideoNo.value && currentVideoUrl.value) {
    if (inlinePlayerRef.value) {
      inlinePlayerRef.value.currentTime = 0
      inlinePlayerRef.value.play()
    }
    return
  }
  try {
    const data = await mediaApi.getMediaDetails(selectedDbId.value, videoNo)
    currentVideoInfo.value = data
    currentVideoNo.value = videoNo
    if (data.file_id) {
      // 优先通过本地代理播放，避免外部 URL 403
      currentVideoUrl.value = `/api/knowledge/databases/${selectedDbId.value}/documents/${data.file_id}/stream?token=${userStore.token}`
    } else if (data.video_url) {
      currentVideoUrl.value = data.video_url
    } else {
      currentVideoUrl.value = ''
    }
  } catch (e) {
    console.error('加载视频播放地址失败:', e)
  }
}

// 从 ref 数据构建关键帧标记
function buildKeyframeMarkers(refs) {
  if (!refs || !refs.length) return
  const markers = []
  for (const refGroup of refs) {
    const duration = Number(refGroup.video?.duration) || 0
    const videoNo = refGroup.video?.video_no || ''
    for (const item of refGroup.refItems || []) {
      const startTime = Number(item.startTime) || 0
      markers.push({
        videoNo,
        startTime,
        type: item.type,
        text: item.text || '',
        percent: duration > 0 ? (startTime / duration) * 100 : 0
      })
    }
  }
  keyframeMarkers.value = markers
}

// === Methods ===
async function loadVideos() {
  if (!selectedDbId.value) {
    videos.value = []
    return
  }
  videosLoading.value = true
  try {
    const result = await videoChatApi.getVideos(selectedDbId.value)
    const videoList = result?.data?.videos || result?.videos || []
    videos.value = Array.isArray(videoList) ? videoList : []
  } catch (e) {
    console.error('加载视频列表失败:', e)
    videos.value = []
  } finally {
    videosLoading.value = false
  }
}

function onDbChange(dbId) {
  selectedDbId.value = dbId
  selectedVideoNos.value = []
  messages.value = []
  sessionId.value = String(Date.now())
  currentVideoUrl.value = ''
  currentVideoInfo.value = null
  currentVideoNo.value = ''
  loadVideos()
}

function toggleVideo(videoNo) {
  const idx = selectedVideoNos.value.indexOf(videoNo)
  if (idx >= 0) {
    selectedVideoNos.value.splice(idx, 1)
  } else {
    selectedVideoNos.value.push(videoNo)
  }
}

function newConversation() {
  messages.value = []
  sessionId.value = String(Date.now())
  inputText.value = ''
  // 重置右侧面板
  videoPanelVisible.value = false
  currentVideoUrl.value = ''
  currentVideoInfo.value = null
  currentVideoNo.value = ''
  keyframeMarkers.value = []
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// === 打字动画 ===
let _contentQueue = ''
let _thinkingQueue = ''
let _typingTimer = null
let _typingTarget = null

function startTyping(aiMsg) {
  _typingTarget = aiMsg
  if (_typingTimer) return
  _typingTimer = setInterval(() => {
    let updated = false
    if (_thinkingQueue.length > 0) {
      const n = Math.min(8, _thinkingQueue.length)
      _typingTarget.thinking += _thinkingQueue.slice(0, n)
      _thinkingQueue = _thinkingQueue.slice(n)
      updated = true
    }
    if (_contentQueue.length > 0) {
      const n = Math.min(5, _contentQueue.length)
      _typingTarget.content += _contentQueue.slice(0, n)
      _contentQueue = _contentQueue.slice(n)
      updated = true
    }
    if (updated) scrollToBottom()
    if (!_thinkingQueue.length && !_contentQueue.length) {
      clearInterval(_typingTimer)
      _typingTimer = null
    }
  }, 20)
}

function flushTyping() {
  if (_typingTimer) {
    clearInterval(_typingTimer)
    _typingTimer = null
  }
  if (_typingTarget) {
    if (_thinkingQueue.length) {
      _typingTarget.thinking += _thinkingQueue
      _thinkingQueue = ''
    }
    if (_contentQueue.length) {
      _typingTarget.content += _contentQueue
      _contentQueue = ''
    }
  }
  _typingTarget = null
}

async function sendMessage(text) {
  const prompt = (text || inputText.value).trim()
  if (!prompt || !hasSelectedVideos.value || loading.value) return

  inputText.value = ''
  messages.value.push({ role: 'user', content: prompt })
  messages.value.push({ role: 'assistant', thinking: '', thinkingTitle: '', refs: [], content: '' })
  const aiMessage = messages.value[messages.value.length - 1]
  loading.value = true
  scrollToBottom()

  // 收到回复后再展开面板和播放视频（见 SSE 处理逻辑）

  abortController.value = new AbortController()

  try {
    const response = await videoChatApi.chatStream(
      selectedDbId.value,
      selectedVideoNos.value,
      prompt,
      sessionId.value,
      abortController.value.signal
    )

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed) continue

        if (trimmed.toLowerCase() === 'data:"done"' || trimmed === 'data: "Done"') continue

        let jsonStr = trimmed
        if (trimmed.startsWith('data:')) {
          jsonStr = trimmed.slice(5).trim()
        }
        if (!jsonStr || jsonStr === '"Done"') continue

        try {
          const data = JSON.parse(jsonStr)

          if (data.code === 'SUCCESS' && data.data === 'Done') continue

          if (
            data.type === 'error' ||
            (data.data && typeof data.data === 'string' && data.data !== 'Done')
          ) {
            aiMessage.content += `\n\n**错误**: ${data.content || data.data || '未知错误'}`
            aiMessage.hasError = true
            scrollToBottom()
            continue
          }

          // 收到第一条有效数据时展开面板并播放视频
          if (!videoPanelVisible.value) {
            videoPanelVisible.value = true
            if (!currentVideoUrl.value && selectedVideoNos.value.length > 0) {
              loadVideoForPlay(selectedVideoNos.value[0])
            }
          }

          switch (data.type) {
            case 'thinking':
              _thinkingQueue += data.content || ''
              if (data.title) aiMessage.thinkingTitle = data.title
              startTyping(aiMessage)
              break
            case 'ref':
              if (data.ref && Array.isArray(data.ref)) {
                aiMessage.refs.push(...data.ref)
                // 如果当前没有视频在播放，加载 ref 中的第一个
                const firstVideoNo = data.ref[0]?.video?.video_no
                if (firstVideoNo && !currentVideoUrl.value) {
                  loadVideoForPlay(firstVideoNo)
                }
                buildKeyframeMarkers(aiMessage.refs)
              }
              break
            case 'content':
              _contentQueue += data.content || ''
              startTyping(aiMessage)
              break
          }

          if (data.sessionId) {
            sessionId.value = data.sessionId
          }

          scrollToBottom()
        } catch {
          // 忽略非 JSON 行
        }
      }
    }
  } catch (e) {
    if (e.name !== 'AbortError') {
      console.error('视频对话失败:', e)
      aiMessage.content += `\n\n**请求失败**: ${e.message}`
      aiMessage.hasError = true
    }
  } finally {
    flushTyping()
    loading.value = false
    abortController.value = null
    scrollToBottom()
  }
}

function stopGeneration() {
  flushTyping()
  if (abortController.value) {
    abortController.value.abort()
  }
}

function usePreset(prompt) {
  sendMessage(prompt)
}

function retryLastMessage() {
  // 移除最后的 AI 回复（含错误），找到对应的用户消息重发
  if (messages.value.length < 2) return
  const lastAi = messages.value[messages.value.length - 1]
  const lastUser = messages.value[messages.value.length - 2]
  if (lastAi.role === 'assistant' && lastUser.role === 'user') {
    const prompt = lastUser.content
    messages.value.splice(-2, 2)
    sendMessage(prompt)
  }
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// ref 引用相关
function formatTime(seconds) {
  if (seconds == null) return ''
  const s = Number(seconds)
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

function playRefItem(refItem, videoInfo) {
  const videoNo = refItem.videoNo || videoInfo?.video_no || ''
  const startTime = Number(refItem.startTime) || 0

  // 如果是当前播放的视频，直接跳转
  if (videoNo === currentVideoNo.value && inlinePlayerRef.value) {
    inlinePlayerRef.value.currentTime = startTime
    inlinePlayerRef.value.play()
    return
  }

  // 否则加载新视频再跳转
  loadVideoForPlay(videoNo).then(() => {
    nextTick(() => {
      if (inlinePlayerRef.value) {
        inlinePlayerRef.value.currentTime = startTime
        inlinePlayerRef.value.play()
      }
    })
  })
}

function getRefTypeLabel(type) {
  const labels = {
    keyframe: '关键帧',
    visual_ts: '画面',
    audio_ts: '音频'
  }
  return labels[type] || type
}

function getMarkerColor(type) {
  const colors = {
    keyframe: 'var(--main-color)',
    visual_ts: '#52c41a',
    audio_ts: '#faad14'
  }
  return colors[type] || 'var(--main-color)'
}

function seekToMarker(marker) {
  if (marker.videoNo && marker.videoNo !== currentVideoNo.value) {
    loadVideoForPlay(marker.videoNo).then(() => {
      nextTick(() => {
        if (inlinePlayerRef.value) {
          inlinePlayerRef.value.currentTime = marker.startTime
          inlinePlayerRef.value.play()
        }
      })
    })
  } else if (inlinePlayerRef.value) {
    inlinePlayerRef.value.currentTime = marker.startTime
    inlinePlayerRef.value.play()
  }
}

onMounted(() => {
  if (databaseStore.databases.length === 0) {
    databaseStore.loadDatabases()
  }
})

onBeforeUnmount(() => {
  flushTyping()
  stopGeneration()
})
</script>

<template>
  <div class="video-chat-page">
    <!-- 左侧：对话区 -->
    <div class="chat-panel">
      <!-- 顶栏 -->
      <div class="chat-header">
        <a-select
          v-model:value="selectedDbId"
          placeholder="选择知识库"
          class="db-select"
          size="small"
          allow-clear
          @change="onDbChange"
        >
          <a-select-option v-for="db in memeresDatabases" :key="db.db_id" :value="db.db_id">
            {{ db.name }}
          </a-select-option>
        </a-select>
        <span v-if="hasSelectedVideos" class="selected-hint">
          已选 {{ selectedVideoNos.length }} 个视频
        </span>
        <div class="header-spacer" />
        <a-button type="text" size="small" @click="newConversation" :disabled="loading">
          <Plus :size="14" style="margin-right: 4px" />
          新对话
        </a-button>
      </div>

      <!-- 视频选择 & 快捷操作 -->
      <div v-if="selectedDbId" class="inline-video-select">
        <div v-if="!videoPanelVisible" class="inline-video-list">
          <a-spin v-if="videosLoading" size="small" />
          <template v-else>
            <div
              v-for="v in videos"
              :key="v.video_no"
              class="inline-video-tag"
              :class="{ selected: selectedVideoNos.includes(v.video_no) }"
              @click="toggleVideo(v.video_no)"
            >
              <a-checkbox :checked="selectedVideoNos.includes(v.video_no)" size="small" />
              <span>{{ v.video_name }}</span>
            </div>
          </template>
        </div>
        <div v-if="hasSelectedVideos" class="inline-presets">
          <a-button
            v-for="p in presetPrompts"
            :key="p.label"
            size="small"
            :disabled="loading"
            @click="usePreset(p.prompt)"
          >
            <component :is="p.icon" :size="12" style="margin-right: 4px" />
            {{ p.label }}
          </a-button>
        </div>
      </div>
      <div ref="messagesContainer" class="messages-area">
        <div v-if="messages.length === 0" class="welcome-hint">
          <Clapperboard :size="40" class="welcome-icon" />
          <div class="welcome-title">长视频分析</div>
          <div class="welcome-desc">
            选择知识库和视频后，与 AI 对话分析视频内容。<br />
            支持视频摘要、执法合规审查、证据提取等功能。
          </div>
        </div>

        <div v-for="(msg, idx) in messages" :key="idx" class="message-wrapper">
          <!-- 用户消息 -->
          <div v-if="msg.role === 'user'" class="message user-message">
            <div class="message-content user-bubble">{{ msg.content }}</div>
          </div>

          <!-- AI 消息 -->
          <div v-else class="message ai-message">
            <!-- Thinking 区域 -->
            <details v-if="msg.thinking" class="thinking-section">
              <summary class="thinking-summary">
                <Brain :size="14" />
                <span>思考过程</span>
              </summary>
              <div class="thinking-content">{{ msg.thinking }}</div>
            </details>

            <!-- Ref 引用卡片 -->
            <div v-if="msg.refs && msg.refs.length" class="ref-cards">
              <div v-for="(refGroup, ri) in msg.refs" :key="ri" class="ref-card">
                <div class="ref-card-header">
                  <Video :size="14" />
                  <span class="ref-video-name">{{
                    refGroup.video?.video_name || '视频引用'
                  }}</span>
                  <span v-if="refGroup.video?.duration" class="ref-duration">
                    {{ formatDuration(refGroup.video.duration) }}
                  </span>
                </div>
                <div class="ref-items">
                  <div
                    v-for="(item, ii) in refGroup.refItems || []"
                    :key="ii"
                    class="ref-item"
                    @click="playRefItem(item, refGroup.video)"
                  >
                    <span class="ref-type-tag">{{ getRefTypeLabel(item.type) }}</span>
                    <span class="ref-time">
                      {{ formatTime(item.startTime) }}
                      <template v-if="item.endTime">- {{ formatTime(item.endTime) }}</template>
                    </span>
                    <span v-if="item.text" class="ref-text" :title="item.text">
                      {{ item.text.length > 60 ? item.text.slice(0, 60) + '...' : item.text }}
                    </span>
                    <Play :size="12" class="ref-play-icon" />
                  </div>
                </div>
              </div>
            </div>

            <!-- Content -->
            <div v-if="msg.content" class="ai-content">
              <MdPreview
                :modelValue="msg.content"
                :theme="themeStore.isDark ? 'dark' : 'light'"
                language="zh-CN"
                :showCodeRowNumber="false"
              />
            </div>

            <!-- 加载指示：thinking 后 content 到来前也显示 -->
            <div
              v-if="loading && idx === messages.length - 1 && !msg.content"
              class="loading-hint"
            >
              <Loader :size="16" class="spin-icon" />
              <span>{{ msg.thinking ? '正在生成回答...' : '分析中...' }}</span>
            </div>

            <!-- 错误重试按钮 -->
            <div v-if="msg.hasError && !loading" class="retry-hint">
              <a-button size="small" @click="retryLastMessage">
                <RotateCw :size="14" style="margin-right: 4px" />
                重试
              </a-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="input-area">
        <div class="input-wrapper">
          <a-textarea
            v-model:value="inputText"
            placeholder="输入问题，分析视频内容..."
            :auto-size="{ minRows: 1, maxRows: 4 }"
            :disabled="!hasSelectedVideos || loading"
            @keydown="handleKeydown"
            class="chat-input"
          />
          <a-button
            v-if="loading"
            type="primary"
            shape="circle"
            size="small"
            class="send-btn"
            @click="stopGeneration"
          >
            <Square :size="14" />
          </a-button>
          <a-button
            v-else
            type="primary"
            shape="circle"
            size="small"
            class="send-btn"
            :disabled="!canSend"
            @click="sendMessage()"
          >
            <Send :size="14" />
          </a-button>
        </div>
        <div v-if="!hasSelectedVideos && selectedDbId" class="input-hint">
          请先选择视频
        </div>
      </div>
    </div>

    <!-- 右侧：视频面板（收到回复后展开） -->
    <div v-show="videoPanelVisible" class="video-panel">
      <!-- 视频播放器 -->
      <div class="player-section">
        <video
          v-if="currentVideoUrl"
          ref="inlinePlayerRef"
          :src="currentVideoUrl"
          controls
          autoplay
          class="inline-player"
        />
        <div v-else class="player-placeholder">
          <Clapperboard :size="32" />
          <span>发送消息后自动播放</span>
        </div>
      </div>

      <!-- 关键帧控制条 -->
      <div v-if="keyframeMarkers.length" class="keyframe-bar">
        <div class="keyframe-header">
          <span class="keyframe-title">关键帧</span>
          <div class="keyframe-legend">
            <span class="legend-item"><i class="legend-dot" style="background: var(--main-color)" />关键帧</span>
            <span class="legend-item"><i class="legend-dot" style="background: #52c41a" />画面</span>
            <span class="legend-item"><i class="legend-dot" style="background: #faad14" />音频</span>
          </div>
        </div>
        <div class="keyframe-track">
          <div
            v-for="(m, mi) in keyframeMarkers"
            :key="mi"
            class="keyframe-dot"
            :style="{ left: m.percent + '%', backgroundColor: getMarkerColor(m.type) }"
            :title="`${getRefTypeLabel(m.type)} ${formatTime(m.startTime)}${m.text ? ' - ' + m.text.slice(0, 30) : ''}`"
            @click="seekToMarker(m)"
          />
        </div>
      </div>

      <!-- 当前视频信息 -->
      <div v-if="currentVideoInfo" class="video-info-card">
        <Video :size="14" />
        <span class="info-name">{{ currentVideoInfo.video_name || '' }}</span>
        <span v-if="currentVideoInfo.duration" class="info-duration">
          {{ formatDuration(currentVideoInfo.duration) }}
        </span>
        <span v-if="currentVideoInfo.resolution_label" class="info-resolution">
          {{ currentVideoInfo.resolution_label }}
        </span>
      </div>

      <!-- 视频列表 -->
      <div class="video-list-section">
        <div class="section-title">
          <Video :size="14" />
          <span>视频列表</span>
          <span v-if="selectedVideoNos.length" class="selected-count">
            {{ selectedVideoNos.length }}
          </span>
        </div>

        <div v-if="!selectedDbId" class="empty-hint">请先选择知识库</div>
        <a-spin v-else-if="videosLoading" class="video-loading" />
        <div v-else-if="videos.length === 0" class="empty-hint">暂无可用视频</div>
        <div v-else class="video-items">
          <div
            v-for="v in videos"
            :key="v.video_no"
            class="video-item"
            :class="{
              selected: selectedVideoNos.includes(v.video_no),
              playing: v.video_no === currentVideoNo
            }"
            @click="toggleVideo(v.video_no)"
          >
            <a-checkbox
              :checked="selectedVideoNos.includes(v.video_no)"
              class="video-checkbox"
            />
            <Video :size="14" class="video-icon" />
            <div class="video-info">
              <div class="video-name" :title="v.video_name">{{ v.video_name }}</div>
              <div class="video-meta" v-if="v.duration">{{ formatDuration(v.duration) }}</div>
            </div>
            <a-tooltip v-if="videoPanelVisible" title="播放">
              <a-button
                type="text"
                size="small"
                class="play-btn"
                :class="{ active: v.video_no === currentVideoNo }"
                @click.stop="loadVideoForPlay(v.video_no)"
              >
                <Play :size="12" />
              </a-button>
            </a-tooltip>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="less" scoped>
.video-chat-page {
  display: flex;
  height: 100%;
  background-color: var(--main-0);
}

// === 左侧对话区 ===
.chat-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--gray-100);

  .db-select {
    width: 180px;
    flex-shrink: 0;
  }

  .selected-hint {
    font-size: 12px;
    color: var(--main-color);
    font-weight: 500;
    white-space: nowrap;
  }

  .header-spacer {
    flex: 1;
  }
}

// 内联视频选择区（右侧面板未展开时）
.inline-video-select {
  padding: 8px 16px;
  border-bottom: 1px solid var(--gray-100);
}

.inline-video-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 6px;
}

.inline-video-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: 14px;
  border: 1px solid var(--gray-150);
  font-size: 12px;
  cursor: pointer;
  color: var(--gray-700);
  transition: all 0.15s;
  white-space: nowrap;

  &:hover {
    border-color: var(--main-color);
  }

  &.selected {
    background-color: var(--color-primary-50);
    border-color: var(--main-color);
    color: var(--main-color);
  }
}

.inline-presets {
  display: flex;
  gap: 6px;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 16px 24px;
}

.welcome-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--gray-400);

  .welcome-icon {
    color: var(--gray-300);
    margin-bottom: 12px;
  }

  .welcome-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--gray-600);
    margin-bottom: 8px;
  }

  .welcome-desc {
    font-size: 13px;
    text-align: center;
    line-height: 1.6;
  }
}

.message-wrapper {
  margin-bottom: 16px;
}

.message {
  max-width: 85%;
}

.user-message {
  margin-left: auto;
}

.user-bubble {
  background-color: var(--main-color);
  color: #fff;
  padding: 8px 14px;
  border-radius: 12px 12px 2px 12px;
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
}

.ai-message {
  max-width: 100%;
}

// Thinking 折叠区
.thinking-section {
  margin-bottom: 8px;
  border: 1px solid var(--gray-100);
  border-radius: 8px;
  overflow: hidden;

  .thinking-summary {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    font-size: 12px;
    color: var(--gray-500);
    cursor: pointer;
    background-color: var(--gray-25);

    &:hover {
      background-color: var(--gray-50);
    }
  }

  .thinking-content {
    padding: 8px 10px;
    font-size: 12px;
    color: var(--gray-600);
    line-height: 1.5;
    white-space: pre-wrap;
    max-height: 200px;
    overflow-y: auto;
  }
}

// Ref 引用卡片
.ref-cards {
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ref-card {
  border: 1px solid var(--gray-150);
  border-radius: 8px;
  overflow: hidden;
}

.ref-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background-color: var(--gray-25);
  font-size: 12px;
  color: var(--gray-700);
  font-weight: 500;

  .ref-video-name {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .ref-duration {
    color: var(--gray-500);
    flex-shrink: 0;
  }
}

.ref-items {
  padding: 4px;
}

.ref-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 6px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background-color 0.15s;

  &:hover {
    background-color: var(--gray-50);

    .ref-play-icon {
      opacity: 1;
    }
  }
}

.ref-type-tag {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 3px;
  background-color: var(--color-primary-50);
  color: var(--main-color);
  font-size: 11px;
}

.ref-time {
  flex-shrink: 0;
  color: var(--gray-600);
  font-family: monospace;
  font-size: 12px;
}

.ref-text {
  flex: 1;
  color: var(--gray-500);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ref-play-icon {
  flex-shrink: 0;
  color: var(--main-color);
  opacity: 0;
  transition: opacity 0.15s;
}

// AI 内容
.ai-content {
  :deep(.md-editor-preview-wrapper) {
    padding: 0;
  }

  :deep(.md-editor-preview) {
    font-size: 14px;
  }
}

.loading-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--gray-400);
  font-size: 13px;
  padding: 4px 0;
}

.retry-hint {
  padding: 6px 0;
}

.spin-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// 输入区
.input-area {
  padding: 12px 24px 16px;
  border-top: 1px solid var(--gray-100);
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.chat-input {
  flex: 1;
  border-radius: 8px;
}

.send-btn {
  flex-shrink: 0;
  margin-bottom: 2px;
}

.input-hint {
  font-size: 12px;
  color: var(--gray-400);
  margin-top: 4px;
}

// === 右侧视频面板 ===
.video-panel {
  flex: 1;
  border-left: 1px solid var(--gray-100);
  display: flex;
  flex-direction: column;
  background-color: var(--main-0);
  overflow-y: auto;
}

// 播放器
.player-section {
  padding: 12px;
  flex-shrink: 0;
}

.inline-player {
  width: 100%;
  aspect-ratio: 16 / 9;
  border-radius: 8px;
  background: #000;
  display: block;
  object-fit: contain;
}

.player-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  aspect-ratio: 16 / 9;
  border-radius: 8px;
  background-color: var(--gray-50);
  color: var(--gray-400);
  font-size: 13px;
}

// 关键帧控制条
.keyframe-bar {
  padding: 0 12px 12px;
  flex-shrink: 0;
}

.keyframe-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.keyframe-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-700);
}

.keyframe-legend {
  display: flex;
  gap: 10px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--gray-500);
}

.legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.keyframe-track {
  position: relative;
  height: 28px;
  background: linear-gradient(to right, var(--gray-100), var(--gray-150));
  border-radius: 14px;
  cursor: pointer;
  border: 1px solid var(--gray-150);
}

.keyframe-dot {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 12px;
  height: 12px;
  border-radius: 50%;
  cursor: pointer;
  transition: transform 0.15s;
  z-index: 1;
  border: 2px solid #fff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);

  &:hover {
    transform: translate(-50%, -50%) scale(1.6);
  }
}

// 视频信息卡
.video-info-card {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  margin: 0 12px;
  border: 1px solid var(--gray-100);
  border-radius: 8px;
  font-size: 13px;
  color: var(--gray-700);

  .info-name {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-weight: 500;
  }

  .info-duration,
  .info-resolution {
    flex-shrink: 0;
    font-size: 12px;
    color: var(--gray-500);
  }
}

// 视频列表
.video-list-section {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 12px;
  overflow: hidden;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  color: var(--gray-600);
  margin-bottom: 8px;

  .selected-count {
    margin-left: auto;
    color: var(--main-color);
    font-weight: 600;
    background-color: var(--color-primary-50);
    padding: 0 6px;
    border-radius: 8px;
    font-size: 11px;
  }
}

.video-items {
  overflow-y: auto;
  flex: 1;
}

.video-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  transition: background-color 0.15s;

  &:hover {
    background-color: var(--gray-50);
  }

  &.selected {
    background-color: var(--color-primary-50);
  }

  &.playing {
    border: 1px solid var(--main-color);
  }
}

.video-checkbox {
  flex-shrink: 0;
}

.video-icon {
  flex-shrink: 0;
  color: var(--gray-500);
}

.video-info {
  min-width: 0;
  flex: 1;
}

.video-name {
  font-size: 13px;
  color: var(--gray-900);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.video-meta {
  font-size: 11px;
  color: var(--gray-500);
  margin-top: 2px;
}

.playing-indicator {
  flex-shrink: 0;
  color: var(--main-color);
}

.play-btn {
  flex-shrink: 0;
  color: var(--gray-400);
  padding: 2px;

  &:hover,
  &.active {
    color: var(--main-color);
  }
}

.video-loading {
  display: flex;
  justify-content: center;
  padding: 20px 0;
}

.empty-hint {
  text-align: center;
  color: var(--gray-400);
  font-size: 13px;
  padding: 20px 0;
}
</style>
