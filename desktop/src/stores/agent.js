import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { agentApi } from '@/apis'

export const useAgentStore = defineStore('agent', () => {
  const agents = ref([])
  const selectedAgentId = ref('')
  const defaultAgentId = ref('')
  const isInitialized = ref(false)
  const loading = ref(false)

  // 配置相关状态
  const agentDetail = ref(null)
  const agentConfig = ref({})
  const originalAgentConfig = ref({})
  const selectedConfigId = ref(null)
  const isLoadingConfig = ref(false)

  const currentAgent = computed(() =>
    agents.value.find((a) => a.id === selectedAgentId.value) || agents.value[0] || null
  )

  const currentAgentName = computed(() => currentAgent.value?.name || '')

  const configurableItems = computed(() => {
    if (!agentDetail.value?.configurable_items) return {}
    const items = { ...agentDetail.value.configurable_items }
    Object.keys(items).forEach((key) => {
      const item = items[key]
      if (item?.x_oap_ui_config) {
        items[key] = { ...item, ...item.x_oap_ui_config }
        delete items[key].x_oap_ui_config
      }
    })
    return items
  })

  const hasConfigChanges = computed(() =>
    JSON.stringify(agentConfig.value) !== JSON.stringify(originalAgentConfig.value)
  )

  async function initialize() {
    if (loading.value) return
    loading.value = true
    try {
      const [agentResult, defaultResult] = await Promise.all([
        agentApi.getAgents(),
        agentApi.getDefaultAgent().catch(() => null)
      ])
      agents.value = agentResult?.agents || []
      if (defaultResult?.agent_id) {
        defaultAgentId.value = defaultResult.agent_id
      }
      // 如果没有选中的智能体，优先选择语音助手，其次默认智能体，最后第一个
      if (!selectedAgentId.value && agents.value.length > 0) {
        const voiceAgent = agents.value.find(
          (a) => a.capabilities && a.capabilities.includes('voice')
        )
        selectedAgentId.value = voiceAgent?.id || defaultAgentId.value || agents.value[0].id
      }
      isInitialized.value = true
    } catch (error) {
      console.error('初始化智能体失败:', error)
    } finally {
      loading.value = false
    }
  }

  function selectAgent(agentId) {
    selectedAgentId.value = agentId
    // 切换智能体时清空配置
    agentDetail.value = null
    agentConfig.value = {}
    originalAgentConfig.value = {}
    selectedConfigId.value = null
  }

  async function fetchAgentDetail(agentId) {
    if (!agentId) return
    try {
      agentDetail.value = await agentApi.getAgentDetail(agentId)
    } catch (e) {
      console.error('获取智能体详情失败:', e)
    }
  }

  async function loadCurrentConfig() {
    const agentId = selectedAgentId.value
    if (!agentId) return

    isLoadingConfig.value = true
    try {
      // 获取配置列表，找到默认配置
      const res = await agentApi.getAgentConfigs(agentId)
      const configs = res?.configs || []
      const defaultConfig = configs.find((c) => c.is_default) || configs[0]
      if (!defaultConfig) return

      selectedConfigId.value = defaultConfig.id

      // 获取配置详情
      const profileRes = await agentApi.getAgentConfigProfile(agentId, defaultConfig.id)
      const configJson = profileRes?.config?.config_json || {}
      const contextConfig = configJson.context || configJson
      const loaded = { ...contextConfig }

      // 确保 configurable_items 已加载
      if (!agentDetail.value) {
        await fetchAgentDetail(agentId)
      }

      // 用 configurableItems 的 default 值补全缺失项
      const items = configurableItems.value
      Object.keys(items).forEach((key) => {
        if (loaded[key] === undefined && items[key].default !== undefined) {
          loaded[key] = items[key].default
        }
      })

      agentConfig.value = loaded
      originalAgentConfig.value = { ...loaded }
    } catch (e) {
      console.error('加载配置失败:', e)
    } finally {
      isLoadingConfig.value = false
    }
  }

  async function saveConfig() {
    const agentId = selectedAgentId.value
    const configId = selectedConfigId.value
    if (!agentId || !configId) return

    await agentApi.updateAgentConfigProfile(agentId, configId, {
      config_json: { context: agentConfig.value }
    })
    originalAgentConfig.value = { ...agentConfig.value }
  }

  function resetConfig() {
    agentConfig.value = { ...originalAgentConfig.value }
  }

  function updateConfigItem(key, value) {
    agentConfig.value[key] = value
  }

  function reset() {
    agents.value = []
    selectedAgentId.value = ''
    defaultAgentId.value = ''
    isInitialized.value = false
    agentDetail.value = null
    agentConfig.value = {}
    originalAgentConfig.value = {}
    selectedConfigId.value = null
  }

  return {
    agents,
    selectedAgentId,
    defaultAgentId,
    isInitialized,
    loading,
    currentAgent,
    currentAgentName,
    agentDetail,
    agentConfig,
    originalAgentConfig,
    selectedConfigId,
    isLoadingConfig,
    configurableItems,
    hasConfigChanges,
    initialize,
    selectAgent,
    fetchAgentDetail,
    loadCurrentConfig,
    saveConfig,
    resetConfig,
    updateConfigItem,
    reset
  }
})
