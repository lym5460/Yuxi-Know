/**
 * 语音错误处理
 * 
 * ASR/TTS 不可用时的降级处理和网络错误提示
 * Validates: Requirements 11.1, 11.2, 11.3
 */

import { message } from 'ant-design-vue'

export const VoiceErrorType = {
  ASR_UNAVAILABLE: 'asr_unavailable',
  TTS_UNAVAILABLE: 'tts_unavailable',
  NETWORK_ERROR: 'network_error',
  PERMISSION_DENIED: 'permission_denied',
  UNKNOWN: 'unknown'
}

export function handleVoiceError(error, type = VoiceErrorType.UNKNOWN) {
  const messages = {
    [VoiceErrorType.ASR_UNAVAILABLE]: '语音识别暂时不可用，请使用文字输入',
    [VoiceErrorType.TTS_UNAVAILABLE]: '语音合成暂时不可用，已切换到文字模式',
    [VoiceErrorType.NETWORK_ERROR]: '网络连接中断，正在重新连接...',
    [VoiceErrorType.PERMISSION_DENIED]: '请允许麦克风权限以使用语音功能',
    [VoiceErrorType.UNKNOWN]: '发生未知错误，请稍后重试'
  }
  
  message.error(messages[type] || messages[VoiceErrorType.UNKNOWN])
  console.error(`Voice error [${type}]:`, error)
}

export function shouldFallbackToText(errorType) {
  return [
    VoiceErrorType.ASR_UNAVAILABLE,
    VoiceErrorType.TTS_UNAVAILABLE,
    VoiceErrorType.PERMISSION_DENIED
  ].includes(errorType)
}
