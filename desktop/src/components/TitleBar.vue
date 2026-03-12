<template>
  <div class="title-bar" :class="{ transparent: transparent }" @mousedown="handleMouseDown">
    <div class="title-bar-left">
      <slot name="left" />
    </div>
    <div class="title-bar-center">
      <slot />
    </div>
    <div class="window-controls">
      <button class="control-btn minimize" @click="handleMinimize" title="最小化">
        <Minus :size="14" />
      </button>
      <button class="control-btn maximize" @click="handleMaximize" title="最大化">
        <Square v-if="!isMaximized" :size="11" />
        <Copy v-else :size="11" />
      </button>
      <button class="control-btn close" @click="handleClose" title="关闭">
        <X :size="14" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Minus, Square, Copy, X } from 'lucide-vue-next'

defineProps({
  transparent: { type: Boolean, default: false }
})

const isMaximized = ref(false)
let appWindow = null
let dragging = false

async function getWindow() {
  if (appWindow) return appWindow
  try {
    const mod = await import('@tauri-apps/api/window')
    appWindow = mod.getCurrentWindow()
    return appWindow
  } catch (e) {
    console.warn('[TitleBar] Tauri window API 不可用:', e)
    return null
  }
}

async function handleMouseDown(e) {
  if (e.button !== 0) return
  if (e.target.closest('button, input, a, [data-no-drag]')) return
  if (isMaximized.value || dragging) return
  dragging = true
  try {
    const win = await getWindow()
    if (win) win.startDragging()
  } catch (e) {
    console.error('[TitleBar] startDragging:', e)
  } finally {
    setTimeout(() => { dragging = false }, 100)
  }
}

async function handleMinimize() {
  try {
    const win = await getWindow()
    if (win) win.minimize()
  } catch (e) {
    console.error('[TitleBar] minimize:', e)
  }
}

async function handleMaximize() {
  try {
    const win = await getWindow()
    if (!win) return
    if (isMaximized.value) {
      win.unmaximize()
      isMaximized.value = false
    } else {
      win.maximize()
      isMaximized.value = true
    }
  } catch (e) {
    console.error('[TitleBar] maximize:', e)
  }
}

async function handleClose() {
  try {
    const win = await getWindow()
    if (win) win.close()
  } catch (e) {
    console.error('[TitleBar] close:', e)
  }
}

let unlisten = null

onMounted(async () => {
  const win = await getWindow()
  if (win) {
    try {
      isMaximized.value = await win.isMaximized()
    } catch {}
  }
})

onUnmounted(() => {
  if (unlisten) unlisten()
})
</script>

<style lang="less" scoped>
.title-bar {
  display: flex;
  align-items: center;
  height: 38px;
  padding: 0 4px 0 12px;
  background: var(--gray-50);
  border-bottom: 1px solid var(--glass-border);
  user-select: none;
  flex-shrink: 0;
  position: relative;
  cursor: default;

  &.transparent {
    background: transparent;
    border-bottom: none;
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    z-index: 100;
  }
}

.title-bar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-bar-center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.window-controls {
  display: flex;
  align-items: center;
  gap: 2px;
}

.control-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 26px;
  border: none;
  background: transparent;
  color: var(--gray-500);
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.15s;
  &:hover {
    background: rgba(0, 212, 255, 0.1);
    color: var(--color-primary-500);
  }

  &.close:hover {
    background: rgba(255, 56, 96, 0.15);
    color: var(--color-danger-500);
  }
}
</style>
