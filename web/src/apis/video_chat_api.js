import { apiAdminGet, apiRequest } from './base'
import { useUserStore, checkAdminPermission } from '@/stores/user'

/**
 * 长视频分析 API
 * 对接 Memeries Video Chat 接口
 */
export const videoChatApi = {
  /**
   * 流式视频对话 - 返回原始 Response 用于读取 SSE
   * @param {string} dbId - Memeries 知识库 ID
   * @param {string[]} videoNos - 选中的视频 ID 列表
   * @param {string} prompt - 用户问题
   * @param {string} sessionId - 会话 ID
   * @param {AbortSignal} signal - 取消信号
   * @returns {Promise<Response>} - 原始 fetch Response
   */
  async chatStream(dbId, videoNos, prompt, sessionId, signal) {
    checkAdminPermission()
    const userStore = useUserStore()
    const response = await fetch('/api/video-chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...userStore.getAuthHeaders()
      },
      body: JSON.stringify({
        db_id: dbId,
        video_nos: videoNos.filter(Boolean),
        prompt,
        session_id: sessionId
      }),
      signal
    })
    if (!response.ok) {
      let msg = `请求失败: ${response.status}`
      try {
        const err = await response.json()
        const detail = err.detail
        msg = typeof detail === 'string' ? detail : JSON.stringify(detail) || msg
      } catch {}
      throw new Error(msg)
    }
    return response
  },

  /**
   * 获取指定知识库的视频列表（仅已解析的）
   * @param {string} dbId - Memeries 知识库 ID
   * @returns {Promise} - 视频列表
   */
  async getVideos(dbId) {
    return apiAdminGet(`/api/video-chat/videos?db_id=${encodeURIComponent(dbId)}`)
  }
}
