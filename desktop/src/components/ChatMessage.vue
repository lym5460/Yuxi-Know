<template>
  <div class="chat-message" :class="[`role-${message.role}`]">
    <div class="message-avatar">
      <div v-if="message.role === 'user'" class="avatar user-avatar">
        <User :size="16" />
      </div>
      <div v-else class="avatar assistant-avatar">
        <Bot :size="16" />
      </div>
    </div>
    <div class="message-body">
      <div class="message-role">{{ message.role === 'user' ? '你' : agentName || '助手' }}</div>

      <!-- Tool call 进度指示器 -->
      <div v-if="toolCalls.length" class="tool-calls">
        <div
          v-for="(tc, idx) in toolCalls"
          :key="idx"
          class="tool-call-item"
          :class="{ done: tc.status === 'done', expanded: expandedSet.has(idx) }"
        >
          <div class="tc-header" @click="toggle(idx)">
            <CircleCheck v-if="tc.status === 'done'" :size="14" class="tc-icon" />
            <LoaderCircle v-else :size="14" class="tc-icon spin" />
            <span class="tc-summary">{{ formatToolCall(tc) }}</span>
            <ChevronsUpDown v-if="!expandedSet.has(idx)" :size="13" class="tc-expand" />
            <ChevronsDownUp v-else :size="13" class="tc-expand" />
          </div>
          <div v-if="expandedSet.has(idx)" class="tc-detail">
            <div v-if="tc.args && Object.keys(tc.args).length" class="tc-params">
              <strong>参数:</strong>
              <pre>{{ JSON.stringify(tc.args, null, 2) }}</pre>
            </div>
            <div v-if="tc.result" class="tc-result">
              <strong>结果:</strong>
              <pre>{{ formatResult(tc.result) }}</pre>
            </div>
          </div>
        </div>
      </div>

      <!-- 用户上传的图片 -->
      <div v-if="message.imageContent" class="message-image" @click="previewVisible = true">
        <img :src="`data:image/jpeg;base64,${message.imageContent}`" alt="用户上传的图片" />
      </div>

      <div class="message-content">
        <div v-if="isStreaming && !message.content" class="thinking-indicator">
          <span class="thinking-dot" />
          <span class="thinking-dot" />
          <span class="thinking-dot" />
          <span class="thinking-text">{{ toolCalls.length ? '正在生成回复' : '思考中' }}</span>
        </div>
        <template v-else>
          <MarkdownRenderer v-if="message.role === 'assistant'" :content="message.content" />
          <div v-else class="user-text">{{ message.content }}</div>
        </template>
      </div>
      <div v-if="isStreaming && message.content" class="streaming-cursor" />
    </div>

    <!-- 图片放大预览 -->
    <Teleport to="body">
      <div v-if="previewVisible" class="image-lightbox" @click="previewVisible = false">
        <img :src="`data:image/jpeg;base64,${message.imageContent}`" alt="图片预览" @click.stop />
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { User, Bot, LoaderCircle, CircleCheck, ChevronsUpDown, ChevronsDownUp } from 'lucide-vue-next'
import MarkdownRenderer from './MarkdownRenderer.vue'

const previewVisible = ref(false)

defineProps({
  message: { type: Object, required: true },
  agentName: { type: String, default: '助手' },
  isStreaming: { type: Boolean, default: false },
  toolCalls: { type: Array, default: () => [] }
})

const expandedSet = reactive(new Set())

function toggle(idx) {
  if (expandedSet.has(idx)) expandedSet.delete(idx)
  else expandedSet.add(idx)
}

const TOOL_LABELS = {
  list_kbs: '列表',
  query_kb: '搜索',
  get_mindmap: '思维导图',
  tavily_search: '网页搜索',
  calculator: '计算',
  write_file: '写文件',
  read_file: '读文件',
  list_directory: '列目录',
  search_file_content: '搜索文件',
  glob: '文件搜索',
  edit_file: '编辑文件',
  write_todos: '待办事项',
  text_to_img: '生成图片',
  mysql_query: 'SQL查询',
  mysql_list_tables: '列出表',
  mysql_describe_table: '描述表'
}

function formatToolCall(tc) {
  const label = TOOL_LABELS[tc.name] || ''
  const parts = [tc.name + (label ? ' ' + label : '')]
  const args = tc.args || {}
  if (args.kb_name) parts.push('知识库: ' + args.kb_name)
  if (args.query_text) parts.push(args.query_text)
  if (args.query) parts.push(args.query)
  return parts.join('  |  ')
}

function formatResult(result) {
  if (!result) return ''
  if (typeof result === 'string') {
    try {
      return JSON.stringify(JSON.parse(result), null, 2)
    } catch {
      return result
    }
  }
  return JSON.stringify(result, null, 2)
}
</script>

<style lang="less" scoped>
.chat-message {
  display: flex;
  gap: 12px;
  padding: 16px 20px;

  &.role-user {
    background: transparent;
  }

  &.role-assistant {
    background: rgba(0, 212, 255, 0.03);
  }
}

.message-avatar {
  flex-shrink: 0;

  .avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .user-avatar {
    background: var(--gray-200);
    color: var(--gray-600);
    border: 1px solid var(--gray-300);
  }

  .assistant-avatar {
    background: rgba(0, 212, 255, 0.15);
    color: var(--color-primary-500);
    border: 1px solid rgba(0, 212, 255, 0.3);
    box-shadow: 0 0 8px rgba(0, 212, 255, 0.2);
  }
}

.message-body {
  flex: 1;
  min-width: 0;
}

.message-role {
  font-size: 13px;
  font-weight: 600;
  color: var(--gray-700);
  margin-bottom: 4px;
}

.message-image {
  display: inline-block;
  max-width: 200px;
  margin-bottom: 8px;
  cursor: pointer;
  border-radius: var(--radius-sm);
  overflow: hidden;
  border: 1px solid var(--glass-border);
  line-height: 0;
  transition: border-color 0.2s;

  &:hover {
    border-color: rgba(0, 212, 255, 0.4);
  }

  img {
    display: block;
    max-width: 100%;
    max-height: 200px;
    object-fit: contain;
  }
}

.message-content {
  .user-text {
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.6;
  }
}

// Tool calls
.tool-calls {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 12px;
  margin-bottom: 10px;
}

.tool-call-item {
  border-radius: var(--radius-sm);
  border: 1px solid rgba(0, 212, 255, 0.1);
  background: rgba(0, 212, 255, 0.04);
  overflow: hidden;

  &.done {
    border-color: rgba(74, 222, 128, 0.2);
    background: rgba(74, 222, 128, 0.04);
  }

  .tc-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 5px 10px;
    cursor: pointer;
    font-size: 12px;
    color: var(--gray-500);
    user-select: none;

    &:hover {
      background: rgba(0, 212, 255, 0.04);
    }
  }

  .tc-icon {
    flex-shrink: 0;
    color: var(--color-primary-500);
  }

  &.done .tc-icon {
    color: #4ade80;
  }

  .tc-summary {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tc-expand {
    flex-shrink: 0;
    color: var(--gray-400);
  }
}

.tc-detail {
  border-top: 1px solid var(--glass-border);
  padding: 8px 10px;
  font-size: 12px;
  color: var(--gray-600);

  strong {
    color: var(--gray-700);
    display: block;
    margin-bottom: 4px;
  }

  pre {
    margin: 0;
    font-size: 11px;
    line-height: 1.4;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 200px;
    overflow-y: auto;
    background: var(--gray-100);
    padding: 8px;
    border-radius: var(--radius-sm);
  }

  .tc-params {
    margin-bottom: 8px;
  }
}

// Thinking & streaming
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 0;

  .thinking-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--color-primary-500);
    opacity: 0.4;
    animation: thinkingPulse 1.4s ease-in-out infinite;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }

  .thinking-text {
    font-size: 13px;
    color: var(--gray-500);
    margin-left: 4px;
  }
}

@keyframes thinkingPulse {
  0%, 60%, 100% { opacity: 0.3; transform: scale(1); }
  30% { opacity: 1; transform: scale(1.2); }
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.streaming-cursor {
  display: inline-block;
  width: 7px;
  height: 16px;
  background: var(--color-primary-500);
  margin-left: 2px;
  animation: blink 1s infinite;
  vertical-align: text-bottom;
  border-radius: 1px;
  box-shadow: 0 0 6px rgba(0, 212, 255, 0.5);
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>

<style lang="less">
.image-lightbox {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.75);
  cursor: pointer;

  img {
    max-width: 90vw;
    max-height: 90vh;
    object-fit: contain;
    border-radius: 8px;
    cursor: default;
  }
}
</style>
