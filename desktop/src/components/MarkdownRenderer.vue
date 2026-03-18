<template>
  <div class="markdown-renderer" @click="handleClick">
    <MdPreview
      editorId="desktop-preview"
      :modelValue="content"
      previewTheme="github"
      :theme="'dark'"
      :showCodeRowNumber="false"
      class="md-preview"
    />
  </div>
</template>

<script setup>
import { MdPreview } from 'md-editor-v3'
import 'md-editor-v3/lib/preview.css'
import { open } from '@tauri-apps/plugin-shell'

defineProps({
  content: { type: String, default: '' }
})

function handleClick(e) {
  const anchor = e.target.closest('a[href]')
  if (!anchor) return
  const href = anchor.getAttribute('href')
  if (href && /^https?:\/\//.test(href)) {
    e.preventDefault()
    open(href)
  }
}
</script>

<style lang="less" scoped>
.markdown-renderer {
  line-height: 1.7;
  font-size: 14px;
  word-break: break-word;
  color: var(--gray-800);

  // 去除 md-editor-v3 默认的外层 padding 和背景
  :deep(.md-editor) {
    background: transparent;
  }

  :deep(.md-editor-preview-wrapper) {
    padding: 0;
  }

  :deep(.md-editor-preview) {
    padding: 0;
    font-size: 14px;
    line-height: 1.7;
    color: var(--gray-800);

    // 代码块
    pre {
      background: var(--gray-100) !important;
      border: 1px solid var(--glass-border);
      border-radius: var(--radius-sm);

      code {
        font-size: 13px;
        font-family: 'SF Mono', 'Fira Code', monospace;
      }
    }

    // 行内代码
    code:not(pre code) {
      background: rgba(0, 212, 255, 0.08);
      color: var(--color-primary-500);
      padding: 2px 5px;
      border-radius: 3px;
      font-size: 13px;
    }

    // 链接
    a {
      color: var(--color-primary-500);
      text-decoration: none;
      &:hover {
        text-decoration: underline;
      }
    }

    // 引用块
    blockquote {
      border-left: 3px solid var(--color-primary-500);
      color: var(--gray-600);
      background: rgba(0, 212, 255, 0.04);
    }

    // 表格
    table {
      th {
        background: rgba(0, 212, 255, 0.06);
      }
    }
  }
}
</style>
