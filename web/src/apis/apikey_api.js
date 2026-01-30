import { apiAdminGet, apiAdminPost, apiAdminPut, apiAdminDelete } from './base'

/**
 * API Key 管理 API 模块
 * 包含 API Key 的增删改查和状态管理功能
 */

const BASE_URL = '/api/apikeys'

// =============================================================================
// === API Key CRUD ===
// =============================================================================

/**
 * 创建 API Key
 * @param {Object} data - 创建数据
 * @param {string} data.name - API Key 名称
 * @param {string} [data.description] - 描述
 * @param {string[]} data.scopes - 权限范围列表
 * @param {number} [data.expires_days] - 过期天数，null 表示永不过期
 * @returns {Promise} - 创建结果，包含完整密钥（仅此一次返回）
 */
export const createApiKey = async (data) => {
  return apiAdminPost(BASE_URL, data)
}

/**
 * 获取 API Key 列表
 * @returns {Promise} - API Key 列表（不含明文密钥）
 */
export const getApiKeys = async () => {
  return apiAdminGet(BASE_URL)
}

/**
 * 获取单个 API Key
 * @param {number} keyId - API Key ID
 * @returns {Promise} - API Key 详情（不含明文密钥）
 */
export const getApiKey = async (keyId) => {
  return apiAdminGet(`${BASE_URL}/${keyId}`)
}

/**
 * 更新 API Key
 * @param {number} keyId - API Key ID
 * @param {Object} data - 更新数据
 * @param {string} [data.name] - API Key 名称
 * @param {string} [data.description] - 描述
 * @param {string[]} [data.scopes] - 权限范围列表
 * @returns {Promise} - 更新后的 API Key
 */
export const updateApiKey = async (keyId, data) => {
  return apiAdminPut(`${BASE_URL}/${keyId}`, data)
}

/**
 * 删除 API Key
 * @param {number} keyId - API Key ID
 * @returns {Promise} - 删除结果
 */
export const deleteApiKey = async (keyId) => {
  return apiAdminDelete(`${BASE_URL}/${keyId}`)
}

// =============================================================================
// === API Key 状态管理 ===
// =============================================================================

/**
 * 启用/禁用 API Key
 * @param {number} keyId - API Key ID
 * @returns {Promise} - 切换后的 API Key
 */
export const toggleApiKey = async (keyId) => {
  return apiAdminPut(`${BASE_URL}/${keyId}/toggle`, {})
}

// =============================================================================
// === 权限范围 ===
// =============================================================================

/**
 * 获取可用权限范围列表
 * @returns {Promise} - 权限范围列表，包含 scope 和 description
 */
export const getAvailableScopes = async () => {
  return apiAdminGet(`${BASE_URL}/scopes`)
}

// =============================================================================
// === 导出为对象形式（兼容现有代码风格）===
// =============================================================================

export const apikeyApi = {
  createApiKey,
  getApiKeys,
  getApiKey,
  updateApiKey,
  deleteApiKey,
  toggleApiKey,
  getAvailableScopes
}

export default apikeyApi
