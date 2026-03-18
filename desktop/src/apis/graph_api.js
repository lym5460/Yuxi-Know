import { apiGet } from './base'

/**
 * 统一图谱接口 (Unified Graph API)
 * 桌面端仅包含查看功能，不含管理功能
 */
export const unifiedApi = {
  /**
   * 获取所有可用的知识图谱列表
   */
  getGraphs: async () => {
    return await apiGet('/api/graph/list', {}, true)
  },

  /**
   * 获取子图数据
   * @param {Object} params - 查询参数
   * @param {string} params.db_id - 图谱ID
   * @param {string} params.node_label - 节点标签/关键词
   * @param {number} params.max_depth - 最大深度
   * @param {number} params.max_nodes - 最大节点数
   */
  getSubgraph: async (params) => {
    const { db_id, node_label = '*', max_depth = 2, max_nodes = null } = params

    if (!db_id) {
      throw new Error('db_id is required')
    }

    const queryParams = new URLSearchParams({
      db_id: db_id,
      node_label: node_label,
      max_depth: max_depth.toString()
    })

    if (max_nodes !== null && max_nodes !== undefined) {
      queryParams.append('max_nodes', max_nodes.toString())
    }

    return await apiGet(`/api/graph/subgraph?${queryParams.toString()}`, {}, true)
  },

  /**
   * 获取图谱统计信息
   * @param {string} db_id - 图谱ID
   */
  getStats: async (db_id) => {
    if (!db_id) {
      throw new Error('db_id is required')
    }

    const queryParams = new URLSearchParams({ db_id })
    return await apiGet(`/api/graph/stats?${queryParams.toString()}`, {}, true)
  }
}
