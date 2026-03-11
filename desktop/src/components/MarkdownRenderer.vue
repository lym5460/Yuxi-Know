<template>
  <div class="markdown-body" v-html="renderedHtml"></div>
</template>

<script setup>
import { computed } from 'vue'
import { Marked } from 'marked'
import { markedHighlight } from 'marked-highlight'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

const props = defineProps({
  content: { type: String, default: '' }
})

const marked = new Marked(
  markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code, lang) {
      if (lang && hljs.getLanguage(lang)) {
        return hljs.highlight(code, { language: lang }).value
      }
      return hljs.highlightAuto(code).value
    }
  })
)

marked.setOptions({
  breaks: true,
  gfm: true
})

const renderedHtml = computed(() => {
  if (!props.content) return ''
  try {
    return marked.parse(props.content)
  } catch {
    return props.content
  }
})
</script>

<style lang="less" scoped>
.markdown-body {
  line-height: 1.7;
  font-size: 14px;
  word-break: break-word;

  :deep(p) {
    margin: 0 0 8px;
    &:last-child { margin-bottom: 0; }
  }

  :deep(pre) {
    background: var(--gray-50);
    border: 1px solid var(--gray-200);
    border-radius: var(--radius-sm);
    padding: 12px;
    overflow-x: auto;
    margin: 8px 0;

    code {
      font-size: 13px;
      font-family: 'SF Mono', 'Fira Code', monospace;
    }
  }

  :deep(code:not(pre code)) {
    background: var(--gray-100);
    padding: 2px 5px;
    border-radius: 3px;
    font-size: 13px;
  }

  :deep(ul), :deep(ol) {
    padding-left: 20px;
    margin: 4px 0;
  }

  :deep(blockquote) {
    margin: 8px 0;
    padding: 4px 12px;
    border-left: 3px solid var(--color-primary-500);
    color: var(--gray-600);
    background: var(--gray-50);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  }

  :deep(table) {
    border-collapse: collapse;
    width: 100%;
    margin: 8px 0;

    th, td {
      border: 1px solid var(--gray-200);
      padding: 6px 10px;
      text-align: left;
    }
    th {
      background: var(--gray-50);
      font-weight: 600;
    }
  }

  :deep(a) {
    color: var(--color-primary-500);
    text-decoration: none;
    &:hover { text-decoration: underline; }
  }

  :deep(h1), :deep(h2), :deep(h3), :deep(h4) {
    margin: 16px 0 8px;
    font-weight: 600;
    line-height: 1.4;
  }
}
</style>
