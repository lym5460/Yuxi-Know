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
      <div class="message-content">
        <MarkdownRenderer v-if="message.role === 'assistant'" :content="message.content" />
        <div v-else class="user-text">{{ message.content }}</div>
      </div>
      <div v-if="isStreaming" class="streaming-cursor" />
    </div>
  </div>
</template>

<script setup>
import { User, Bot } from 'lucide-vue-next'
import MarkdownRenderer from './MarkdownRenderer.vue'

defineProps({
  message: { type: Object, required: true },
  agentName: { type: String, default: '助手' },
  isStreaming: { type: Boolean, default: false }
})
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

.message-content {
  .user-text {
    white-space: pre-wrap;
    word-break: break-word;
    line-height: 1.6;
  }
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
