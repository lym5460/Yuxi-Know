<template>
  <div class="floating-chat">
    <TransitionGroup name="float-msg" tag="div" class="float-list">
      <div
        v-for="item in visibleItems"
        :key="item.id"
        class="float-item"
        :class="item.role"
        :style="{ opacity: item.opacity }"
      >
        <span class="float-role">{{ item.role === 'user' ? '我' : 'AI' }}</span>
        <span class="float-text">{{ item.displayContent }}</span>
      </div>
    </TransitionGroup>
    <div v-if="interim" class="float-interim">
      <span class="interim-dot" /><span class="interim-dot" /><span class="interim-dot" />
      <span class="interim-text">{{ interim }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onUnmounted, computed } from 'vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  interim: { type: String, default: '' },
  maxVisible: { type: Number, default: 6 },
  fadeDuration: { type: Number, default: 12000 }
})

const visibleItems = ref([])
let idCounter = 0
let fadeTimers = []

function addItem(role, content) {
  const id = ++idCounter
  const item = {
    id,
    role,
    content,
    displayContent: content.length > 120 ? content.slice(0, 120) + '…' : content,
    opacity: 1,
    addedAt: Date.now()
  }
  visibleItems.value.push(item)

  // 超出最大数量，移除最旧的
  while (visibleItems.value.length > props.maxVisible) {
    visibleItems.value.shift()
  }

  // 定时淡出
  const timer = setTimeout(() => {
    fadeOut(id)
  }, props.fadeDuration)
  fadeTimers.push(timer)

  return id
}

function fadeOut(id) {
  const idx = visibleItems.value.findIndex(i => i.id === id)
  if (idx === -1) return
  // 渐变淡出
  const item = visibleItems.value[idx]
  item.opacity = 0
  setTimeout(() => {
    const i = visibleItems.value.findIndex(v => v.id === id)
    if (i !== -1) visibleItems.value.splice(i, 1)
  }, 500)
}

// 跟踪上次处理到的消息索引和最后一条 assistant 消息的 ID
let lastProcessedCount = 0
let lastAssistantItemId = null
let lastAssistantContent = ''

watch(() => props.messages, (msgs) => {
  if (!msgs || msgs.length === 0) {
    fadeTimers.forEach(clearTimeout)
    fadeTimers = []
    visibleItems.value = []
    lastProcessedCount = 0
    lastAssistantItemId = null
    lastAssistantContent = ''
    return
  }

  // 新消息
  if (msgs.length > lastProcessedCount) {
    for (let i = lastProcessedCount; i < msgs.length; i++) {
      const msg = msgs[i]
      if (msg.role === 'user') {
        addItem('user', msg.content)
        lastAssistantItemId = null
        lastAssistantContent = ''
      } else if (msg.role === 'assistant') {
        if (msg.content) {
          lastAssistantItemId = addItem('assistant', msg.content)
          lastAssistantContent = msg.content
        }
      }
    }
    lastProcessedCount = msgs.length
  }

  // 检测最后一条 assistant 消息内容变化（流式更新）
  if (msgs.length > 0) {
    const last = msgs[msgs.length - 1]
    if (last.role === 'assistant' && last.content !== lastAssistantContent) {
      const item = visibleItems.value.find(v => v.id === lastAssistantItemId)
      if (item) {
        item.content = last.content
        item.displayContent = last.content.length > 120
          ? last.content.slice(0, 120) + '…'
          : last.content
        item.opacity = 1
      }
      lastAssistantContent = last.content
    }
  }
}, { deep: true, immediate: true })

onUnmounted(() => {
  fadeTimers.forEach(clearTimeout)
})
</script>

<style lang="less" scoped>
.floating-chat {
  position: absolute;
  inset: 0;
  pointer-events: none;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 16px 20px;
  overflow: hidden;
}

.float-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
}

.float-item {
  max-width: 75%;
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 13px;
  line-height: 1.5;
  backdrop-filter: blur(12px);
  transition: opacity 0.5s ease;
  animation: floatIn 0.4s ease-out;

  &.user {
    align-self: flex-end;
    background: rgba(0, 212, 255, 0.12);
    border: 1px solid rgba(0, 212, 255, 0.2);
    color: var(--gray-800);
  }

  &.assistant {
    align-self: flex-start;
    background: rgba(120, 80, 255, 0.1);
    border: 1px solid rgba(120, 80, 255, 0.18);
    color: var(--gray-800);
  }

  .float-role {
    font-size: 11px;
    font-weight: 600;
    margin-right: 6px;
    opacity: 0.6;
  }

  .float-text {
    word-break: break-all;
  }
}

// TransitionGroup 动画
.float-msg-enter-active {
  transition: all 0.4s ease-out;
}
.float-msg-leave-active {
  transition: all 0.4s ease-in;
  position: absolute;
}
.float-msg-enter-from {
  opacity: 0;
  transform: translateY(20px) scale(0.95);
}
.float-msg-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.95);
}
.float-msg-move {
  transition: transform 0.3s ease;
}

@keyframes floatIn {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.float-interim {
  align-self: flex-start;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  margin-top: 4px;
  border-radius: 12px;
  background: rgba(0, 212, 255, 0.06);
  border: 1px solid rgba(0, 212, 255, 0.12);
  font-size: 12px;
  color: var(--color-primary-500);
  font-style: italic;

  .interim-dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--color-primary-500);
    animation: dotPulse 1.2s ease-in-out infinite;
    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }

  .interim-text {
    margin-left: 4px;
  }
}

@keyframes dotPulse {
  0%, 100% { opacity: 0.3; transform: scale(0.8); }
  50% { opacity: 1; transform: scale(1.2); }
}
</style>
