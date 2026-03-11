/**
 * Tauri 桌面能力集成
 * - 全局快捷键（按住说话）
 * - 视频置顶窗口管理
 */

import { ref, onUnmounted } from 'vue'

let tauriModules = null

async function ensureTauriModules() {
  if (tauriModules) return tauriModules
  try {
    const [shortcut, api] = await Promise.all([
      import('@tauri-apps/plugin-global-shortcut'),
      import('@tauri-apps/api/core')
    ])
    tauriModules = { shortcut, invoke: api.invoke }
    return tauriModules
  } catch (e) {
    console.warn('Tauri 模块加载失败（可能在浏览器中运行）:', e)
    return null
  }
}

/**
 * 全局快捷键 - 按住说话
 */
export function useGlobalShortcut() {
  const isRegistered = ref(false)
  const defaultShortcut = 'CmdOrCtrl+Shift+V'

  async function register(shortcutKey, { onPress, onRelease } = {}) {
    const modules = await ensureTauriModules()
    if (!modules) return

    try {
      await modules.shortcut.register(shortcutKey || defaultShortcut, (event) => {
        if (event.state === 'Pressed') {
          onPress?.()
        } else if (event.state === 'Released') {
          onRelease?.()
        }
      })
      isRegistered.value = true
    } catch (e) {
      console.error('注册全局快捷键失败:', e)
    }
  }

  async function unregister(shortcutKey) {
    const modules = await ensureTauriModules()
    if (!modules) return

    try {
      await modules.shortcut.unregister(shortcutKey || defaultShortcut)
      isRegistered.value = false
    } catch (e) {
      console.error('注销全局快捷键失败:', e)
    }
  }

  onUnmounted(() => {
    if (isRegistered.value) {
      unregister()
    }
  })

  return { isRegistered, register, unregister }
}

/**
 * 视频置顶窗口管理
 */
export function useVideoWindow() {
  async function openVideoWindow() {
    const modules = await ensureTauriModules()
    if (!modules) return
    try {
      await modules.invoke('open_video_window')
    } catch (e) {
      console.error('打开视频窗口失败:', e)
    }
  }

  async function closeVideoWindow() {
    try {
      const { WebviewWindow } = await import('@tauri-apps/api/webviewWindow')
      const videoWin = await WebviewWindow.getByLabel('video')
      if (videoWin) await videoWin.close()
    } catch (e) {
      console.error('关闭视频窗口失败:', e)
    }
  }

  async function sendMediaCommand(payload, retries = 5) {
    try {
      const { emitTo } = await import('@tauri-apps/api/event')
      await emitTo('video', 'media-command', payload)
    } catch (e) {
      if (retries > 0) {
        await new Promise((r) => setTimeout(r, 500))
        return sendMediaCommand(payload, retries - 1)
      }
      console.error('发送媒体命令失败:', e)
    }
  }

  return { openVideoWindow, closeVideoWindow, sendMediaCommand }
}
