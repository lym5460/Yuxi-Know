<template>
  <div class="graph-view">
    <TitleBar>
      <template #left>
        <button class="icon-btn" @click="$router.push('/chat')" title="返回聊天">
          <ArrowLeft :size="16" />
        </button>
        <div class="page-title">知识图谱</div>
        <a-select
          v-model:value="state.selectedDbId"
          style="width: 200px"
          :options="state.dbOptions"
          @change="handleDbChange"
          :loading="state.loadingDatabases"
          placeholder="选择知识库"
          size="small"
        />
      </template>
    </TitleBar>

    <div class="graph-body">
      <GraphCanvas
        ref="graphRef"
        :graph-data="graph.graphData"
        :graph-info="graphInfo"
        :highlight-keywords="[state.searchInput]"
        @node-click="graph.handleNodeClick"
        @edge-click="graph.handleEdgeClick"
        @canvas-click="graph.handleCanvasClick"
      >
        <template #top>
          <div class="actions">
            <div class="actions-left">
              <a-input
                v-model:value="state.searchInput"
                placeholder="输入要查询的实体 (*为全部)"
                style="width: 260px"
                @keydown.enter="onSearch"
                allow-clear
                size="small"
              >
                <template #suffix>
                  <Search v-if="!state.searchLoading" :size="14" class="search-icon" @click="onSearch" />
                  <a-spin v-else size="small" />
                </template>
              </a-input>
              <a-input-number
                v-model:value="sampleNodeCount"
                placeholder="节点数"
                style="width: 100px"
                :min="1"
                :step="100"
                size="small"
                @keydown.enter="loadSampleNodes"
              >
                <template #suffix>
                  <RefreshCw v-if="!graph.fetching" :size="13" class="search-icon" @click="loadSampleNodes" />
                  <a-spin v-else size="small" />
                </template>
              </a-input-number>
            </div>
            <div class="actions-right">
              <button class="action-btn" @click="exportGraphData" title="导出数据">
                <Download :size="14" />
                <span>导出</span>
              </button>
            </div>
          </div>
        </template>
        <template #content>
          <a-empty v-if="graph.graphData.nodes.length === 0 && !graph.fetching" description="暂无数据" />
        </template>
      </GraphCanvas>

      <GraphDetailPanel
        :visible="graph.showDetailDrawer"
        :item="graph.selectedItem"
        :type="graph.selectedItemType"
        @close="graph.handleCanvasClick"
      />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { ArrowLeft, Search, RefreshCw, Download } from 'lucide-vue-next'
import TitleBar from '@/components/TitleBar.vue'
import GraphCanvas from '@/components/GraphCanvas.vue'
import GraphDetailPanel from '@/components/GraphDetailPanel.vue'
import { useGraph } from '@/composables/useGraph'
import { unifiedApi } from '@/apis/graph_api'

const graphRef = ref(null)
const sampleNodeCount = ref(1500)

const graph = reactive(useGraph(graphRef))

const state = reactive({
  loadingDatabases: false,
  searchInput: '',
  searchLoading: false,
  selectedDbId: null,
  dbOptions: [],
  stats: null
})

const graphInfo = computed(() => ({
  node_count: state.stats?.total_nodes || 0,
  edge_count: state.stats?.total_edges || 0
}))

const loadDatabases = async () => {
  state.loadingDatabases = true
  try {
    const res = await unifiedApi.getGraphs()
    if (res.success && res.data) {
      state.dbOptions = res.data.map((db) => ({
        label: `${db.name} (${db.type})`,
        value: db.id,
        type: db.type
      }))

      if (state.dbOptions.length > 0) {
        state.selectedDbId = state.dbOptions[0].value
      }
    }
  } catch (error) {
    console.error('Failed to load databases:', error)
    message.error('加载知识库列表失败')
  } finally {
    state.loadingDatabases = false
  }
}

const handleDbChange = () => {
  graph.clearGraph()
  state.searchInput = ''
  state.stats = null
  loadStats()
  loadSampleNodes()
}

const loadStats = () => {
  if (!state.selectedDbId) return
  unifiedApi
    .getStats(state.selectedDbId)
    .then((res) => {
      if (res.success) {
        state.stats = res.data
      }
    })
    .catch((e) => console.error(e))
}

const loadSampleNodes = () => {
  if (!state.selectedDbId) return

  const maxNodes = sampleNodeCount.value || null
  graph.fetching = true

  unifiedApi
    .getSubgraph({
      db_id: state.selectedDbId,
      node_label: '*',
      max_nodes: maxNodes
    })
    .then((data) => {
      const result = data.data
      graph.updateGraphData(result.nodes, result.edges)
    })
    .catch((error) => {
      console.error(error)
      message.error(error.message || '加载节点失败')
    })
    .finally(() => (graph.fetching = false))
}

const onSearch = () => {
  if (state.searchLoading || !state.selectedDbId) return

  const maxNodes = sampleNodeCount.value || null
  state.searchLoading = true

  unifiedApi
    .getSubgraph({
      db_id: state.selectedDbId,
      node_label: state.searchInput || '*',
      max_nodes: maxNodes
    })
    .then((data) => {
      const result = data.data
      if (!result || !result.nodes || !result.edges) {
        throw new Error('返回数据格式不正确')
      }
      graph.updateGraphData(result.nodes, result.edges)
      if (graph.graphData.nodes.length === 0) {
        message.info('未找到相关实体')
      }
    })
    .catch((error) => {
      console.error('查询错误:', error)
      message.error(`查询出错：${error.message || '未知错误'}`)
    })
    .finally(() => (state.searchLoading = false))
}

const exportGraphData = () => {
  const dataStr = JSON.stringify(
    {
      nodes: graph.graphData.nodes,
      edges: graph.graphData.edges,
      graphInfo: state.stats,
      source: state.selectedDbId,
      exportTime: new Date().toISOString()
    },
    null,
    2
  )

  const dataBlob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement('a')
  link.href = url
  link.download = `graph-data-${state.selectedDbId}-${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)

  message.success('图谱数据已导出')
}

onMounted(async () => {
  await loadDatabases()
  if (state.selectedDbId) {
    loadStats()
    loadSampleNodes()
  }
})
</script>

<style lang="less" scoped>
.graph-view {
  width: 100%;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #0a0e17;
}

.page-title {
  font-size: 14px;
  font-weight: 600;
  color: #e4eaf2;
  margin-right: 12px;
}

.graph-body {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 0 16px;
}

.actions-left,
.actions-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-icon {
  cursor: pointer;
  color: #667788;
  transition: color 0.2s;

  &:hover {
    color: #00d4ff;
  }
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid #1e2a3a;
  border-radius: 4px;
  color: #8899aa;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    color: #e4eaf2;
    border-color: #2a3a4e;
    background: rgba(255, 255, 255, 0.08);
  }
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: #8899aa;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #e4eaf2;
  }
}
</style>
