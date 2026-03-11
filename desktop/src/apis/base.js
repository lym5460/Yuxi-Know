import { useUserStore } from '@/stores/user'
import { useServerStore } from '@/stores/server'
import { message } from 'ant-design-vue'

function resolveUrl(url) {
  const serverStore = useServerStore()
  return serverStore.resolveUrl(url)
}

export async function apiRequest(url, options = {}, requiresAuth = true, responseType = 'json') {
  const fullUrl = resolveUrl(url)
  try {
    const isFormData = options?.body instanceof FormData
    const requestOptions = {
      ...options,
      headers: {
        ...(!isFormData ? { 'Content-Type': 'application/json' } : {}),
        ...options.headers
      }
    }

    if (requiresAuth) {
      const userStore = useUserStore()
      if (!userStore.isLoggedIn) throw new Error('用户未登录')
      Object.assign(requestOptions.headers, userStore.getAuthHeaders())
    }

    const response = await fetch(fullUrl, requestOptions)

    if (!response.ok) {
      let errorMessage = `请求失败: ${response.status}`
      try {
        const errorData = await response.json()
        errorMessage = errorData.detail || errorData.message || errorMessage
      } catch {}

      if (response.status === 401) {
        const userStore = useUserStore()
        message.error('登录已过期，请重新登录')
        if (userStore.isLoggedIn) userStore.logout()
        setTimeout(() => window.__router__?.push('/login'), 1500)
        throw new Error('未授权')
      }

      throw new Error(errorMessage)
    }

    if (responseType === 'blob') return response
    if (responseType === 'json') {
      const ct = response.headers.get('Content-Type')
      return ct?.includes('application/json') ? await response.json() : await response.text()
    }
    if (responseType === 'text') return await response.text()
    return response
  } catch (error) {
    console.error('API请求错误:', error)
    throw error
  }
}

export function apiGet(url, options = {}, requiresAuth = true, responseType = 'json') {
  return apiRequest(url, { method: 'GET', ...options }, requiresAuth, responseType)
}

export function apiPost(url, data = {}, options = {}, requiresAuth = true, responseType = 'json') {
  return apiRequest(
    url,
    { method: 'POST', body: data instanceof FormData ? data : JSON.stringify(data), ...options },
    requiresAuth,
    responseType
  )
}

export function apiPut(url, data = {}, options = {}, requiresAuth = true, responseType = 'json') {
  return apiRequest(
    url,
    { method: 'PUT', body: data instanceof FormData ? data : JSON.stringify(data), ...options },
    requiresAuth,
    responseType
  )
}

export function apiDelete(url, options = {}, requiresAuth = true, responseType = 'json') {
  return apiRequest(url, { method: 'DELETE', ...options }, requiresAuth, responseType)
}
