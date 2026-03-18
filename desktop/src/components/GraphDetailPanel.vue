<template>
  <transition name="slide-fade">
    <div class="detail-card" v-if="visible">
      <a-card :bordered="false" size="small" class="info-card">
        <template #title>
          <div class="card-title">
            <span>{{ title }}</span>
            <button class="close-btn" @click="$emit('close')">
              <X :size="14" />
            </button>
          </div>
        </template>

        <div class="card-content">
          <template v-if="item">
            <a-descriptions :column="1" size="small" :bordered="true">
              <template v-if="type === 'node'">
                <a-descriptions-item label="名称">{{ item.data?.label }}</a-descriptions-item>
                <a-descriptions-item label="ID">{{ item.id }}</a-descriptions-item>

                <template v-if="item.data?.original?.properties">
                  <a-descriptions-item
                    v-for="(value, key) in item.data.original.properties"
                    :key="key"
                    :label="key"
                  >
                    {{ value }}
                  </a-descriptions-item>
                </template>

                <a-descriptions-item label="标签" v-if="item.data?.original?.labels">
                  <div class="tags-container">
                    <a-tag v-for="tag in item.data.original.labels" :key="tag" color="blue">{{
                      tag
                    }}</a-tag>
                  </div>
                </a-descriptions-item>
              </template>

              <template v-else-if="type === 'edge'">
                <a-descriptions-item label="类型">{{ item.data?.label }}</a-descriptions-item>

                <template v-if="item.data?.original?.properties">
                  <a-descriptions-item
                    v-for="(value, key) in filteredEdgeProperties"
                    :key="key"
                    :label="key"
                  >
                    {{ value }}
                  </a-descriptions-item>
                </template>
              </template>
            </a-descriptions>
          </template>
        </div>
      </a-card>
    </div>
  </transition>
</template>

<script setup>
import { computed } from 'vue'
import { X } from 'lucide-vue-next'

const props = defineProps({
  visible: Boolean,
  item: Object,
  type: String
})

defineEmits(['close'])

const title = computed(() => {
  return props.type === 'node' ? '节点详情' : '关系详情'
})

const filteredEdgeProperties = computed(() => {
  if (!props.item?.data?.original?.properties) return {}

  const properties = props.item.data.original.properties
  const hiddenFields = ['source_id', 'target_id', '_id', 'truncate']
  const filtered = {}

  Object.keys(properties).forEach((key) => {
    if (!hiddenFields.includes(key)) {
      filtered[key] = properties[key]
    }
  })

  return filtered
})
</script>

<style scoped lang="less">
.detail-card {
  position: absolute;
  top: 80px;
  right: 24px;
  width: 300px;
  max-height: calc(100% - 100px);
  overflow-y: auto;
  z-index: 1000;
  pointer-events: auto;

  .info-card {
    background: #141a26;
    border: 1px solid #1e2a3a;
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);

    :deep(.ant-card-head) {
      border-bottom: 1px solid #1e2a3a;
      min-height: auto;
      padding: 0 16px;
    }

    :deep(.ant-card-body) {
      padding: 12px;
    }

    :deep(.ant-descriptions-item-label),
    :deep(.ant-descriptions-item-content) {
      font-size: 12px;
      padding: 4px 8px !important;
    }
  }

  .card-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 13px;
    font-weight: 600;
    color: #e4eaf2;

    .close-btn {
      background: none;
      border: none;
      color: #667788;
      cursor: pointer;
      padding: 4px;
      display: flex;
      align-items: center;
      border-radius: 4px;
      transition: all 0.2s;

      &:hover {
        color: #e4eaf2;
        background: rgba(255, 255, 255, 0.05);
      }
    }
  }

  .tags-container {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
}

.slide-fade-enter-active {
  transition: all 0.3s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s cubic-bezier(1, 0.5, 0.8, 1);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(20px);
  opacity: 0;
}
</style>
