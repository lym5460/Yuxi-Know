<template>
  <a-drawer
    :open="open"
    title="智能体配置"
    placement="right"
    :width="380"
    @close="$emit('close')"
    class="config-drawer"
  >
    <div v-if="agentStore.isLoadingConfig" class="loading-state">
      <LoaderCircle :size="24" class="spin" />
      <span>加载配置中...</span>
    </div>

    <div v-else-if="isEmptyConfig" class="empty-config">
      该智能体没有可配置项
    </div>

    <a-form v-else layout="vertical" class="config-form">
      <template v-for="(item, key) in agentStore.configurableItems" :key="key">
        <a-form-item :label="item.name || key" class="config-item">
          <p v-if="item.description" class="config-desc">{{ item.description }}</p>

          <!-- 系统提示词 -->
          <a-textarea
            v-if="item.template_metadata?.kind === 'prompt'"
            :value="agentStore.agentConfig[key]"
            @update:value="(val) => agentStore.updateConfigItem(key, val)"
            :rows="6"
            :placeholder="`默认: ${item.default || ''}`"
            class="config-textarea"
          />

          <!-- 模型选择 -->
          <a-select
            v-else-if="item.template_metadata?.kind === 'llm'"
            :value="agentStore.agentConfig[key]"
            @update:value="(val) => agentStore.updateConfigItem(key, val)"
            :placeholder="`默认: ${item.default || ''}`"
            show-search
            allow-clear
            class="config-select"
            popupClassName="config-dropdown"
          >
            <a-select-option v-for="opt in getOptions(item)" :key="getOptValue(opt)" :value="getOptValue(opt)">
              {{ getOptLabel(opt) }}
            </a-select-option>
          </a-select>

          <!-- 多选列表类型 (tools/knowledges/mcps/skills) -->
          <div v-else-if="isListType(key, item)" class="list-config">
            <div class="list-header">
              <span class="list-count">已选择 {{ (agentStore.agentConfig[key] || []).length }} 项</span>
              <a-button
                v-if="(agentStore.agentConfig[key] || []).length > 0"
                type="link"
                size="small"
                @click="agentStore.updateConfigItem(key, [])"
                class="clear-btn"
              >清空</a-button>
            </div>
            <div class="options-grid">
              <div
                v-for="opt in getOptions(item)"
                :key="getOptValue(opt)"
                class="option-card"
                :class="{ selected: isSelected(key, getOptValue(opt)) }"
                @click="toggleOption(key, getOptValue(opt))"
              >
                <span class="option-label">{{ getOptLabel(opt) }}</span>
                <Check v-if="isSelected(key, getOptValue(opt))" :size="14" />
                <Plus v-else :size="14" />
              </div>
            </div>
          </div>

          <!-- 布尔 -->
          <a-switch
            v-else-if="typeof agentStore.agentConfig[key] === 'boolean'"
            :checked="agentStore.agentConfig[key]"
            @update:checked="(val) => agentStore.updateConfigItem(key, val)"
          />

          <!-- 单选 -->
          <a-select
            v-else-if="item.options?.length > 0 && (item.type === 'str' || item.type === 'select')"
            :value="agentStore.agentConfig[key]"
            @update:value="(val) => agentStore.updateConfigItem(key, val)"
            class="config-select"
            popupClassName="config-dropdown"
          >
            <a-select-option v-for="opt in item.options" :key="opt" :value="opt">
              {{ typeof opt === 'object' ? opt.label || opt.name : opt }}
            </a-select-option>
          </a-select>

          <!-- 数字 -->
          <a-input-number
            v-else-if="item.type === 'number'"
            :value="agentStore.agentConfig[key]"
            @update:value="(val) => agentStore.updateConfigItem(key, val)"
            :placeholder="`默认: ${item.default || ''}`"
            class="config-input-number"
          />

          <!-- 滑块 -->
          <a-slider
            v-else-if="item.type === 'slider'"
            :value="agentStore.agentConfig[key]"
            @update:value="(val) => agentStore.updateConfigItem(key, val)"
            :min="item.min"
            :max="item.max"
            :step="item.step"
          />

          <!-- 默认文本输入 -->
          <a-input
            v-else
            :value="agentStore.agentConfig[key]"
            @update:value="(val) => agentStore.updateConfigItem(key, val)"
            :placeholder="`默认: ${item.default || ''}`"
            class="config-input"
          />
        </a-form-item>
      </template>
    </a-form>

    <template #footer>
      <div class="drawer-footer">
        <a-button @click="handleReset" :disabled="!agentStore.hasConfigChanges">重置</a-button>
        <a-button
          type="primary"
          @click="handleSave"
          :loading="saving"
          :disabled="!agentStore.hasConfigChanges"
        >保存</a-button>
      </div>
    </template>
  </a-drawer>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import { LoaderCircle, Check, Plus } from 'lucide-vue-next'
import { useAgentStore } from '@/stores/agent'
import { systemApi } from '@/apis/agent_api'

const props = defineProps({
  open: { type: Boolean, default: false }
})

const emit = defineEmits(['close'])
const agentStore = useAgentStore()
const saving = ref(false)

// 动态选项数据
const modelOptions = ref([])
const toolOptions = ref([])
const knowledgeOptions = ref([])
const skillOptions = ref([])

const isEmptyConfig = computed(() => Object.keys(agentStore.configurableItems).length === 0)

// 打开抽屉时加载配置和动态选项
watch(() => props.open, async (val) => {
  if (val && agentStore.selectedAgentId) {
    await agentStore.fetchAgentDetail(agentStore.selectedAgentId)
    await agentStore.loadCurrentConfig()
    loadDynamicOptions()
  }
})

async function loadDynamicOptions() {
  const items = agentStore.configurableItems
  const kinds = Object.values(items).map((v) => v.template_metadata?.kind)

  const tasks = []

  if (kinds.includes('llm')) {
    tasks.push(
      systemApi.getConfig()
        .then((config) => {
          const modelNames = config?.model_names || {}
          const providerStatus = config?.model_provider_status || {}
          const options = []
          for (const [provider, info] of Object.entries(modelNames)) {
            if (!providerStatus[provider]) continue
            for (const model of info.models || []) {
              options.push(`${provider}/${model}`)
            }
          }
          modelOptions.value = options
        })
        .catch(() => {})
    )
  }

  if (kinds.includes('tools')) {
    tasks.push(
      systemApi.getTools()
        .then((res) => {
          toolOptions.value = (res?.data || []).map((t) => ({
            id: t.id,
            name: t.name || t.id,
            description: t.description || ''
          }))
        })
        .catch(() => {})
    )
  }

  if (kinds.includes('knowledges')) {
    tasks.push(
      systemApi.getAccessibleDatabases()
        .then((res) => {
          knowledgeOptions.value = (res?.databases || []).map((db) => ({
            name: db.name || db.db_id,
            db_id: db.db_id,
            description: db.description || ''
          }))
        })
        .catch(() => {})
    )
  }

  if (kinds.includes('skills')) {
    tasks.push(
      systemApi.getSkills()
        .then((res) => {
          skillOptions.value = (res?.data || []).map((s) => ({
            id: s.slug,
            name: s.slug,
            description: s.description || ''
          }))
        })
        .catch(() => {})
    )
  }

  await Promise.all(tasks)
}

function isListType(key, item) {
  return item.type === 'list' ||
    ['tools', 'knowledges', 'mcps', 'skills'].includes(item.template_metadata?.kind)
}

function getOptions(item) {
  const kind = item.template_metadata?.kind
  if (kind === 'llm') return modelOptions.value
  if (kind === 'tools') return toolOptions.value.length > 0 ? toolOptions.value : (item.options || [])
  if (kind === 'knowledges') return knowledgeOptions.value.length > 0 ? knowledgeOptions.value : (item.options || [])
  if (kind === 'skills') return skillOptions.value.length > 0 ? skillOptions.value : (item.options || [])
  return item.options || []
}

function getOptValue(opt) {
  if (typeof opt === 'object' && opt !== null) {
    return opt.id || opt.value || opt.name || opt.db_id || opt.slug
  }
  return opt
}

function getOptLabel(opt) {
  if (typeof opt === 'object' && opt !== null) {
    return opt.name || opt.label || opt.id || opt.db_id || opt.slug
  }
  return opt
}

function isSelected(key, val) {
  return (agentStore.agentConfig[key] || []).includes(val)
}

function toggleOption(key, val) {
  const current = [...(agentStore.agentConfig[key] || [])]
  const idx = current.indexOf(val)
  if (idx > -1) current.splice(idx, 1)
  else current.push(val)
  agentStore.updateConfigItem(key, current)
}

async function handleSave() {
  saving.value = true
  try {
    await agentStore.saveConfig()
    message.success('配置已保存')
  } catch (e) {
    message.error('保存失败: ' + e.message)
  } finally {
    saving.value = false
  }
}

function handleReset() {
  agentStore.resetConfig()
}
</script>

<style lang="less" scoped>
.loading-state, .empty-config {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: var(--gray-500);
  gap: 8px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.config-form {
  :deep(.ant-form-item-label > label) {
    color: var(--gray-800);
    font-size: 13px;
    font-weight: 500;
  }
}

.config-item {
  margin-bottom: 16px;
}

.config-desc {
  margin: 0 0 6px;
  font-size: 12px;
  color: var(--gray-500);
  line-height: 1.4;
}

.config-textarea,
.config-input,
.config-input-number {
  width: 100%;
}

.config-select {
  width: 100%;
}

// 多选列表
.list-config {
  .list-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .list-count {
    font-size: 12px;
    color: var(--gray-500);
  }

  .clear-btn {
    font-size: 12px;
    padding: 0;
    height: auto;
  }
}

.options-grid {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.option-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
  color: var(--gray-600);
  font-size: 13px;
  background: transparent;

  &:hover {
    border-color: rgba(0, 212, 255, 0.3);
    color: var(--gray-800);
  }

  &.selected {
    border-color: rgba(0, 212, 255, 0.4);
    background: rgba(0, 212, 255, 0.08);
    color: var(--color-primary-500);
  }

  .option-label {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-right: 8px;
  }
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>

<style lang="less">
// 全局样式覆盖 ant-design-vue 抽屉的暗色主题
.config-drawer {
  .ant-drawer-content {
    background: var(--gray-50);
  }

  .ant-drawer-header {
    background: var(--gray-50);
    border-bottom: 1px solid var(--glass-border);

    .ant-drawer-title {
      color: var(--gray-900);
      font-size: 15px;
    }

    .ant-drawer-close {
      color: var(--gray-500);

      &:hover {
        color: var(--color-primary-500);
      }
    }
  }

  .ant-drawer-body {
    padding: 16px;
    background: var(--gray-50);
  }

  .ant-drawer-footer {
    background: var(--gray-50);
    border-top: 1px solid var(--glass-border);
  }

  // 表单控件暗色适配
  .ant-input,
  .ant-input-number,
  .ant-select-selector,
  .ant-input-number-input {
    background: var(--gray-100) !important;
    border-color: var(--glass-border) !important;
    color: var(--gray-900) !important;

    &:hover,
    &:focus {
      border-color: rgba(0, 212, 255, 0.4) !important;
    }
  }

  .ant-input::placeholder,
  .ant-input-number-input::placeholder {
    color: var(--gray-400) !important;
  }

  .ant-select-selection-placeholder {
    color: var(--gray-400) !important;
  }

  .ant-select-selection-item {
    color: var(--gray-900) !important;
  }

  .ant-select-arrow {
    color: var(--gray-500) !important;
  }

  .ant-switch {
    background: var(--gray-300);

    &.ant-switch-checked {
      background: var(--color-primary-500);
    }
  }

  .ant-slider-rail {
    background: var(--gray-300);
  }

  .ant-slider-track {
    background: var(--color-primary-500);
  }

  .ant-slider-handle {
    border-color: var(--color-primary-500);
  }

  .ant-btn-default {
    background: var(--gray-100);
    border-color: var(--glass-border);
    color: var(--gray-800);

    &:hover {
      border-color: rgba(0, 212, 255, 0.4);
      color: var(--color-primary-500);
    }

    &:disabled {
      opacity: 0.4;
      color: var(--gray-500);
    }
  }

  .ant-btn-primary {
    background: var(--color-primary-500);
    border-color: var(--color-primary-500);

    &:hover {
      background: var(--color-primary-600);
    }

    &:disabled {
      opacity: 0.4;
    }
  }
}

// 下拉菜单暗色适配
.config-dropdown {
  .ant-select-dropdown {
    background: var(--gray-100) !important;
    border: 1px solid var(--glass-border);
  }

  .ant-select-item {
    color: var(--gray-800) !important;

    &-option-active {
      background: rgba(0, 212, 255, 0.08) !important;
    }

    &-option-selected {
      background: rgba(0, 212, 255, 0.15) !important;
      color: var(--color-primary-500) !important;
    }
  }
}
</style>
