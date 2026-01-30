<template>
  <div class="apikey-management">
    <!-- 头部区域 -->
    <div class="header-section">
      <div class="header-content">
        <h3 class="title">API Key 管理</h3>
        <p class="description">
          管理第三方应用访问凭证。创建后请立即保存密钥，密钥仅显示一次。
        </p>
      </div>
      <a-button type="primary" @click="showCreateModal" class="add-btn">
        <template #icon><PlusOutlined /></template>
        创建 API Key
      </a-button>
    </div>

    <!-- 主内容区域 -->
    <div class="content-section">
      <a-spin :spinning="state.loading">
        <div v-if="state.error" class="error-message">
          <a-alert type="error" :message="state.error" show-icon />
        </div>

        <div class="cards-container">
          <div v-if="state.apiKeys.length === 0" class="empty-state">
            <a-empty description="暂无 API Key" />
          </div>
          <div v-else class="apikey-cards-grid">
            <div v-for="apiKey in state.apiKeys" :key="apiKey.id" class="apikey-card">
              <div class="card-header">
                <div class="apikey-info-main">
                  <div class="apikey-icon">
                    <KeyRound :size="20" />
                  </div>
                  <div class="apikey-info-content">
                    <div class="name-status-row">
                      <h4 class="apikey-name">{{ apiKey.name }}</h4>
                      <a-switch
                        :checked="apiKey.is_active"
                        size="small"
                        @change="handleToggle(apiKey)"
                        :loading="state.toggleLoading === apiKey.id"
                      />
                    </div>
                    <div class="key-prefix-row">
                      <code class="key-prefix">{{ apiKey.key_prefix }}...</code>
                      <a-tag v-if="!apiKey.is_active" color="error" class="status-tag">已禁用</a-tag>
                      <a-tag v-else-if="isExpired(apiKey)" color="warning" class="status-tag">已过期</a-tag>
                    </div>
                  </div>
                </div>
              </div>

              <div class="card-content">
                <div v-if="apiKey.description" class="info-item description-item">
                  <span class="info-value description-text">{{ apiKey.description }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">权限范围:</span>
                  <span class="info-value scopes-text">
                    <a-tag v-for="scope in apiKey.scopes" :key="scope" size="small" class="scope-tag">
                      {{ getScopeLabel(scope) }}
                    </a-tag>
                  </span>
                </div>
                <div class="info-item">
                  <span class="info-label">创建时间:</span>
                  <span class="info-value time-text">{{ formatTime(apiKey.created_at) }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">过期时间:</span>
                  <span class="info-value time-text">{{ apiKey.expires_at ? formatTime(apiKey.expires_at) : '永不过期' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">最后使用:</span>
                  <span class="info-value time-text">{{ apiKey.last_used_at ? formatTime(apiKey.last_used_at) : '从未使用' }}</span>
                </div>
              </div>

              <div class="card-actions">
                <a-tooltip title="编辑">
                  <a-button type="text" size="small" @click="showEditModal(apiKey)" class="action-btn">
                    <EditOutlined />
                    <span>编辑</span>
                  </a-button>
                </a-tooltip>
                <a-tooltip title="删除">
                  <a-button type="text" size="small" danger @click="confirmDelete(apiKey)" class="action-btn">
                    <DeleteOutlined />
                    <span>删除</span>
                  </a-button>
                </a-tooltip>
              </div>
            </div>
          </div>
        </div>
      </a-spin>
    </div>

    <!-- 创建/编辑模态框 -->
    <a-modal
      v-model:open="state.modalVisible"
      :title="state.editMode ? '编辑 API Key' : '创建 API Key'"
      @ok="handleFormSubmit"
      :confirmLoading="state.submitLoading"
      @cancel="state.modalVisible = false"
      :maskClosable="false"
      width="480px"
      class="apikey-modal"
    >
      <a-form layout="vertical" class="apikey-form">
        <a-form-item label="名称" required class="form-item">
          <a-input
            v-model:value="state.form.name"
            placeholder="请输入 API Key 名称"
            size="large"
            :maxlength="100"
          />
        </a-form-item>

        <a-form-item label="描述" class="form-item">
          <a-textarea
            v-model:value="state.form.description"
            placeholder="请输入描述（可选）"
            :rows="2"
            :maxlength="500"
          />
        </a-form-item>

        <a-form-item label="权限范围" required class="form-item">
          <a-checkbox-group v-model:value="state.form.scopes" class="scopes-checkbox-group">
            <div v-for="scope in state.availableScopes" :key="scope.scope" class="scope-checkbox-item">
              <a-checkbox :value="scope.scope">
                <span class="scope-name">{{ scope.scope }}</span>
                <span class="scope-desc">{{ scope.description }}</span>
              </a-checkbox>
            </div>
          </a-checkbox-group>
        </a-form-item>

        <a-form-item v-if="!state.editMode" label="过期时间" class="form-item">
          <a-select v-model:value="state.form.expires_days" size="large" placeholder="选择过期时间">
            <a-select-option :value="null">永不过期</a-select-option>
            <a-select-option :value="7">7 天</a-select-option>
            <a-select-option :value="30">30 天</a-select-option>
            <a-select-option :value="90">90 天</a-select-option>
            <a-select-option :value="180">180 天</a-select-option>
            <a-select-option :value="365">365 天</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 密钥显示模态框 -->
    <a-modal
      v-model:open="state.keyDisplayVisible"
      title="API Key 创建成功"
      :footer="null"
      :maskClosable="false"
      :closable="false"
      width="520px"
      class="key-display-modal"
    >
      <div class="key-display-content">
        <a-alert
          type="warning"
          show-icon
          class="key-warning"
        >
          <template #message>
            <span>请立即复制并保存此密钥，关闭后将无法再次查看！</span>
          </template>
        </a-alert>

        <div class="key-display-box">
          <code class="full-key">{{ state.createdKey }}</code>
          <a-button type="primary" @click="copyKey" class="copy-btn">
            <template #icon><CopyOutlined /></template>
            {{ state.copied ? '已复制' : '复制密钥' }}
          </a-button>
        </div>

        <div class="key-display-footer">
          <a-button type="primary" @click="closeKeyDisplay" :disabled="!state.copied">
            我已保存密钥
          </a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { reactive, onMounted } from 'vue'
import { notification, Modal } from 'ant-design-vue'
import { PlusOutlined, EditOutlined, DeleteOutlined, CopyOutlined } from '@ant-design/icons-vue'
import { KeyRound } from 'lucide-vue-next'
import { apikeyApi } from '@/apis/apikey_api'
import { formatDateTime } from '@/utils/time'

// 状态管理
const state = reactive({
  loading: false,
  submitLoading: false,
  toggleLoading: null,
  apiKeys: [],
  availableScopes: [],
  error: null,
  modalVisible: false,
  editMode: false,
  editKeyId: null,
  form: {
    name: '',
    description: '',
    scopes: [],
    expires_days: null
  },
  keyDisplayVisible: false,
  createdKey: '',
  copied: false
})

// 格式化时间
const formatTime = (timeStr) => formatDateTime(timeStr)

// 判断是否过期
const isExpired = (apiKey) => {
  if (!apiKey.expires_at) return false
  return new Date(apiKey.expires_at) < new Date()
}

// 获取权限范围标签
const getScopeLabel = (scope) => {
  const found = state.availableScopes.find(s => s.scope === scope)
  return found ? scope.split(':')[1] : scope
}

// 获取 API Key 列表
const fetchApiKeys = async () => {
  try {
    state.loading = true
    state.error = null
    const data = await apikeyApi.getApiKeys()
    state.apiKeys = data
  } catch (error) {
    console.error('获取 API Key 列表失败:', error)
    state.error = '获取 API Key 列表失败'
  } finally {
    state.loading = false
  }
}

// 获取可用权限范围
const fetchAvailableScopes = async () => {
  try {
    const data = await apikeyApi.getAvailableScopes()
    state.availableScopes = data
  } catch (error) {
    console.error('获取权限范围失败:', error)
  }
}

// 显示创建模态框
const showCreateModal = () => {
  state.editMode = false
  state.editKeyId = null
  state.form = {
    name: '',
    description: '',
    scopes: [],
    expires_days: null
  }
  state.modalVisible = true
}

// 显示编辑模态框
const showEditModal = (apiKey) => {
  state.editMode = true
  state.editKeyId = apiKey.id
  state.form = {
    name: apiKey.name,
    description: apiKey.description || '',
    scopes: [...apiKey.scopes],
    expires_days: null
  }
  state.modalVisible = true
}

// 处理表单提交
const handleFormSubmit = async () => {
  if (!state.form.name.trim()) {
    notification.error({ message: '请输入 API Key 名称' })
    return
  }

  if (state.form.scopes.length === 0) {
    notification.error({ message: '请至少选择一个权限范围' })
    return
  }

  try {
    state.submitLoading = true

    if (state.editMode) {
      await apikeyApi.updateApiKey(state.editKeyId, {
        name: state.form.name.trim(),
        description: state.form.description.trim() || null,
        scopes: state.form.scopes
      })
      notification.success({ message: 'API Key 更新成功' })
    } else {
      const result = await apikeyApi.createApiKey({
        name: state.form.name.trim(),
        description: state.form.description.trim() || null,
        scopes: state.form.scopes,
        expires_days: state.form.expires_days
      })
      // 显示创建的密钥
      state.createdKey = result.key
      state.copied = false
      state.keyDisplayVisible = true
    }

    state.modalVisible = false
    await fetchApiKeys()
  } catch (error) {
    console.error('操作失败:', error)
    notification.error({
      message: '操作失败',
      description: error.message || '请稍后重试'
    })
  } finally {
    state.submitLoading = false
  }
}

// 复制密钥
const copyKey = async () => {
  try {
    await navigator.clipboard.writeText(state.createdKey)
    state.copied = true
    notification.success({ message: '密钥已复制到剪贴板' })
  } catch {
    notification.error({ message: '复制失败，请手动复制' })
  }
}

// 关闭密钥显示
const closeKeyDisplay = () => {
  state.keyDisplayVisible = false
  state.createdKey = ''
  state.copied = false
}

// 切换启用/禁用状态
const handleToggle = async (apiKey) => {
  try {
    state.toggleLoading = apiKey.id
    await apikeyApi.toggleApiKey(apiKey.id)
    await fetchApiKeys()
    notification.success({
      message: apiKey.is_active ? 'API Key 已禁用' : 'API Key 已启用'
    })
  } catch (error) {
    console.error('切换状态失败:', error)
    notification.error({
      message: '操作失败',
      description: error.message || '请稍后重试'
    })
  } finally {
    state.toggleLoading = null
  }
}

// 确认删除
const confirmDelete = (apiKey) => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除 API Key "${apiKey.name}" 吗？删除后使用该密钥的应用将无法访问系统。`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        state.loading = true
        await apikeyApi.deleteApiKey(apiKey.id)
        notification.success({ message: 'API Key 已删除' })
        await fetchApiKeys()
      } catch (error) {
        console.error('删除失败:', error)
        notification.error({
          message: '删除失败',
          description: error.message || '请稍后重试'
        })
      } finally {
        state.loading = false
      }
    }
  })
}

// 组件挂载时获取数据
onMounted(async () => {
  await Promise.all([fetchApiKeys(), fetchAvailableScopes()])
})
</script>

<style lang="less" scoped>
.apikey-management {
  margin-top: 12px;
  min-height: 50vh;

  .header-section {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;

    .header-content {
      flex: 1;

      .description {
        font-size: 14px;
        color: var(--gray-600);
        margin: 0;
        line-height: 1.4;
        margin-bottom: 16px;
      }
    }
  }

  .content-section {
    overflow: hidden;

    .error-message {
      padding: 16px 0;
    }

    .cards-container {
      .empty-state {
        padding: 60px 20px;
        text-align: center;
      }

      .apikey-cards-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 16px;

        .apikey-card {
          background: var(--gray-0);
          border: 1px solid var(--gray-150);
          border-radius: 8px;
          padding: 12px;
          padding-bottom: 6px;
          transition: all 0.2s ease;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

          &:hover {
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            border-color: var(--gray-200);
          }

          .card-header {
            margin-bottom: 10px;

            .apikey-info-main {
              display: flex;
              gap: 12px;
              align-items: flex-start;

              .apikey-icon {
                width: 40px;
                height: 40px;
                border-radius: 8px;
                background: var(--main-50);
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
                color: var(--main-600);
              }

              .apikey-info-content {
                flex: 1;
                min-width: 0;

                .name-status-row {
                  display: flex;
                  align-items: center;
                  justify-content: space-between;
                  gap: 8px;
                  margin-bottom: 4px;

                  .apikey-name {
                    margin: 0;
                    font-size: 15px;
                    font-weight: 600;
                    color: var(--gray-900);
                    line-height: 1.2;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                  }
                }

                .key-prefix-row {
                  display: flex;
                  align-items: center;
                  gap: 8px;

                  .key-prefix {
                    font-size: 12px;
                    color: var(--gray-600);
                    font-family: 'Monaco', 'Consolas', monospace;
                    background: var(--gray-50);
                    padding: 2px 6px;
                    border-radius: 4px;
                  }

                  .status-tag {
                    font-size: 11px;
                  }
                }
              }
            }
          }

          .card-content {
            .info-item {
              display: flex;
              justify-content: space-between;
              align-items: flex-start;
              padding: 4px 0;
              border-bottom: 1px solid var(--gray-25);

              &:last-child {
                border-bottom: none;
              }

              &.description-item {
                display: block;
                margin-bottom: 4px;

                .description-text {
                  font-size: 13px;
                  color: var(--gray-700);
                  line-height: 1.4;
                }
              }

              .info-label {
                font-size: 12px;
                color: var(--gray-600);
                font-weight: 500;
                min-width: 70px;
                flex-shrink: 0;
              }

              .info-value {
                font-size: 12px;
                color: var(--gray-900);
                text-align: right;
                flex: 1;

                &.time-text {
                  color: var(--gray-700);
                }

                &.scopes-text {
                  display: flex;
                  flex-wrap: wrap;
                  gap: 4px;
                  justify-content: flex-end;

                  .scope-tag {
                    font-size: 11px;
                    margin: 0;
                  }
                }
              }
            }
          }

          .card-actions {
            display: flex;
            justify-content: flex-end;
            gap: 6px;
            padding-top: 6px;
            border-top: 1px solid var(--gray-25);

            .action-btn {
              display: flex;
              align-items: center;
              gap: 4px;
              padding: 4px 8px;
              border-radius: 6px;
              transition: all 0.2s ease;
              font-size: 12px;

              span {
                font-size: 12px;
              }

              &:hover {
                background: var(--gray-25);
              }

              &.ant-btn-dangerous:hover {
                background: var(--gray-25);
                border-color: var(--color-error-500);
                color: var(--color-error-500);
              }
            }
          }
        }
      }
    }
  }
}

.apikey-modal {
  :deep(.ant-modal-header) {
    padding: 20px 24px;
    border-bottom: 1px solid var(--gray-150);

    .ant-modal-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--gray-900);
    }
  }

  :deep(.ant-modal-body) {
    padding: 24px;
  }

  .apikey-form {
    .form-item {
      margin-bottom: 20px;

      :deep(.ant-form-item-label) {
        padding-bottom: 4px;

        label {
          font-weight: 500;
          color: var(--gray-900);
        }
      }
    }

    .scopes-checkbox-group {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .scope-checkbox-item {
        padding: 8px 12px;
        background: var(--gray-25);
        border-radius: 6px;
        border: 1px solid var(--gray-100);

        :deep(.ant-checkbox-wrapper) {
          display: flex;
          align-items: flex-start;
          width: 100%;

          .ant-checkbox {
            margin-top: 2px;
          }

          span:last-child {
            display: flex;
            flex-direction: column;
            gap: 2px;
          }
        }

        .scope-name {
          font-weight: 500;
          color: var(--gray-900);
          font-family: 'Monaco', 'Consolas', monospace;
          font-size: 13px;
        }

        .scope-desc {
          font-size: 12px;
          color: var(--gray-600);
        }
      }
    }
  }
}

.key-display-modal {
  :deep(.ant-modal-header) {
    padding: 20px 24px;
    border-bottom: 1px solid var(--gray-150);

    .ant-modal-title {
      font-size: 16px;
      font-weight: 600;
      color: var(--color-success-700);
    }
  }

  :deep(.ant-modal-body) {
    padding: 24px;
  }

  .key-display-content {
    .key-warning {
      margin-bottom: 16px;
    }

    .key-display-box {
      background: var(--gray-50);
      border: 1px solid var(--gray-150);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;

      .full-key {
        display: block;
        font-family: 'Monaco', 'Consolas', monospace;
        font-size: 14px;
        color: var(--gray-900);
        word-break: break-all;
        margin-bottom: 12px;
        padding: 12px;
        background: var(--gray-0);
        border-radius: 4px;
        border: 1px solid var(--gray-100);
      }

      .copy-btn {
        width: 100%;
      }
    }

    .key-display-footer {
      display: flex;
      justify-content: flex-end;
    }
  }
}
</style>
