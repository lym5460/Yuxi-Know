import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { agentApi } from '@/apis'

export const useAgentStore = defineStore('agent', () => {
  const agents = ref([])
  const selectedAgentId = ref('')
  const defaultAgentId = ref('')
  const isInitialized = ref(false)
  const loading = ref(false)

  const currentAgent = computed(() =>
    agents.value.find((a) => a.id === selectedAgentId.value) || agents.value[0] || null
  )

  const currentAgentName = computed(() => currentAgent.value?.name || '')

  async function initialize() {
    if (loading.value) return
    loading.value = true
    try {
      const [agentList, defaultAgent] = await Promise.all([
        agentApi.getAgents(),
        agentApi.getDefaultAgent().catch(() => null)
      ])
      agents.value = agentList || []
      if (defaultAgent?.agent_id) {
        defaultAgentId.value = defaultAgent.agent_id
      }
      // 如果没有选中的智能体，选择默认的或第一个
      if (!selectedAgentId.value && agents.value.length > 0) {
        selectedAgentId.value = defaultAgentId.value || agents.value[0].id
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
  }

  function reset() {
    agents.value = []
    selectedAgentId.value = ''
    defaultAgentId.value = ''
    isInitialized.value = false
  }

  return {
    agents,
    selectedAgentId,
    defaultAgentId,
    isInitialized,
    loading,
    currentAgent,
    currentAgentName,
    initialize,
    selectAgent,
    reset
  }
})
