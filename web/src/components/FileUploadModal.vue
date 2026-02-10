<template>
  <a-modal v-model:open="visible" title="添加文件" width="800px" @cancel="handleCancel">
    <template #footer>
      <div class="footer-container">
        <a-button type="link" class="help-link-btn" @click="openDocLink">
          <CircleHelp :size="14" /> 文档处理说明
        </a-button>
        <div class="footer-buttons">
          <a-button key="back" @click="handleCancel">取消</a-button>
          <a-button
            key="submit"
            type="primary"
            @click="chunkData"
            :loading="chunkLoading"
            :disabled="fileList.length === 0"
          >
            添加到知识库
          </a-button>
        </div>
      </div>
    </template>

    <div class="add-files-content">
      <!-- 1. 顶部操作栏 -->
      <div class="top-action-bar">
        <div class="mode-switch">
          <a-segmented
            v-model:value="uploadMode"
            :options="uploadModeOptions"
            class="custom-segmented"
          />
        </div>
      </div>

      <!-- 2. 配置面板 -->
      <div class="settings-panel">
        <!-- 第一行：存储位置 + OCR 引擎 -->
        <div :class="['setting-row', { 'two-cols': !isMemeries }]">
          <div class="col-item">
            <div class="setting-label">存储位置</div>
            <div class="setting-content flex-row">
              <a-tree-select
                v-model:value="selectedFolderId"
                show-search
                class="folder-select"
                :dropdown-style="{ maxHeight: '400px', overflow: 'auto' }"
                placeholder="选择目标文件夹（默认为根目录）"
                allow-clear
                tree-default-expand-all
                :tree-data="folderTreeData"
                tree-node-filter-prop="title"
              >
              </a-tree-select>
            </div>
            <p class="param-description">选择文件保存的目标文件夹</p>
          </div>
          <div class="col-item" v-if="!isMemeries">
            <div class="setting-label">
              OCR 引擎
              <a-tooltip title="检查服务状态">
                <ReloadOutlined
                  class="action-icon refresh-icon"
                  :class="{ spinning: ocrHealthChecking }"
                  @click="checkOcrHealth"
                />
              </a-tooltip>
            </div>
            <div class="setting-content">
              <a-select
                v-model:value="chunkParams.enable_ocr"
                :options="enableOcrOptions"
                style="width: 100%"
                :disabled="ocrHealthChecking"
                class="ocr-select"
              />
              <p class="param-description">
                <template v-if="!isOcrEnabled"> 不启用 OCR，仅处理文本文件 </template>
                <template v-else-if="selectedOcrStatus === 'healthy'">
                  {{ selectedOcrMessage || '服务正常' }}
                </template>
                <template v-else-if="selectedOcrStatus === 'unknown'">
                  点击刷新图标检查服务状态
                </template>
                <template v-else>
                  {{ selectedOcrMessage || '服务异常' }}
                </template>
              </p>
            </div>
          </div>
        </div>

        <!-- 第三行：自动入库配置 -->
        <div class="setting-row" v-if="!isMemeries">
          <div class="col-item">
            <div class="setting-label">
              <a-checkbox v-model:checked="autoIndex">上传后自动入库</a-checkbox>
            </div>
            <div class="setting-content" v-if="autoIndex">
              <template v-if="!isGraphBased">
                <ChunkParamsConfig :temp-chunk-params="indexParams" :show-qa-split="true" />
              </template>
              <template v-else>
                <div class="lightrag-tip">
                  <Info :size="14" style="margin-right: 6px" />
                  <span>LightRAG 将使用默认参数自动入库</span>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- PDF/图片OCR提醒 (Alert样式优化) -->
      <div v-if="!isMemeries && hasPdfOrImageFiles && !isOcrEnabled" class="inline-alert warning">
        <Info :size="16" />
        <span>检测到PDF或图片文件，建议启用 OCR 以提取文本内容</span>
      </div>

      <!-- 文件上传区域 -->
      <div class="upload-area">
        <a-upload-dragger
          class="custom-dragger"
          v-model:fileList="fileList"
          name="file"
          :multiple="true"
          :directory="isFolderUpload"
          :disabled="chunkLoading"
          :accept="acceptedFileTypes"
          :before-upload="beforeUpload"
          :customRequest="customRequest"
          :action="'/api/knowledge/files/upload?db_id=' + databaseId"
          :headers="getAuthHeaders()"
          @change="handleFileUpload"
          @drop="handleDrop"
        >
          <p class="ant-upload-text">点击或将文件拖拽到此处</p>
          <p class="ant-upload-hint">支持类型: {{ uploadHint }}</p>
          <div class="zip-tip" v-if="hasZipFiles">📦 ZIP包将自动解压提取 Markdown 与图片</div>
        </a-upload-dragger>
      </div>

      <!-- 同名文件提示 -->
      <div v-if="sameNameFiles.length > 0" class="conflict-files-panel">
        <div class="panel-header">
          <Info :size="14" class="icon-warning" />
          <span>已存在同名文件 ({{ sameNameFiles.length }})</span>
        </div>
        <div class="file-list-scroll">
          <div v-for="file in sameNameFiles" :key="file.file_id" class="conflict-item">
            <div class="file-meta">
              <span class="fname" :title="file.filename">{{ file.filename }}</span>
              <span class="ftime">{{ formatFileTime(file.created_at) }}</span>
            </div>
            <div class="file-actions">
              <a-button
                type="text"
                size="small"
                class="action-btn download"
                @click="downloadSameNameFile(file)"
              >
                <Download :size="14" />
              </a-button>
              <a-button
                type="text"
                size="small"
                danger
                class="action-btn delete"
                @click="deleteSameNameFile(file)"
              >
                <Trash2 :size="14" />
              </a-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { message, Upload, Tooltip, Modal } from 'ant-design-vue'
import { useUserStore } from '@/stores/user'
import { useDatabaseStore } from '@/stores/database'
import { ocrApi } from '@/apis/system_api'
import { fileApi, documentApi } from '@/apis/knowledge_api'
import { CheckCircleFilled, ReloadOutlined } from '@ant-design/icons-vue'
import { FileUp, FolderUp, RotateCw, CircleHelp, Info, Download, Trash2 } from 'lucide-vue-next'
import { h } from 'vue'
import ChunkParamsConfig from '@/components/ChunkParamsConfig.vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  folderTree: {
    type: Array,
    default: () => []
  },
  currentFolderId: {
    type: String,
    default: null
  },
  isFolderMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:visible', 'success'])

const store = useDatabaseStore()

// 文件夹选择相关
const selectedFolderId = ref(null)
const folderTreeData = computed(() => {
  // 转换 folderTree 数据为 TreeSelect 需要的格式
  const transformData = (nodes) => {
    return nodes
      .map((node) => {
        if (!node.is_folder) return null
        return {
          title: node.filename,
          value: node.file_id,
          key: node.file_id,
          children: node.children ? transformData(node.children).filter(Boolean) : []
        }
      })
      .filter(Boolean)
  }
  return transformData(props.folderTree)
})

watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      selectedFolderId.value = props.currentFolderId
      isFolderUpload.value = props.isFolderMode
      uploadMode.value = props.isFolderMode ? 'folder' : 'file'
      loadSupportedFileTypes()
    }
  }
)

const DEFAULT_SUPPORTED_TYPES = ['.txt', '.pdf', '.jpg', '.jpeg', '.md', '.docx']
const MEDIA_SUPPORTED_TYPES = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg']

const normalizeExtensions = (extensions) => {
  if (!Array.isArray(extensions)) {
    return []
  }
  const normalized = extensions
    .map((ext) => (typeof ext === 'string' ? ext.trim().toLowerCase() : ''))
    .filter((ext) => ext.length > 0)
    .map((ext) => (ext.startsWith('.') ? ext : `.${ext}`))

  return Array.from(new Set(normalized)).sort()
}

const supportedFileTypes = ref(normalizeExtensions(DEFAULT_SUPPORTED_TYPES))

const applySupportedFileTypes = (extensions) => {
  const normalized = normalizeExtensions(extensions)
  if (normalized.length > 0) {
    supportedFileTypes.value = normalized
  } else {
    supportedFileTypes.value = normalizeExtensions(DEFAULT_SUPPORTED_TYPES)
  }
}

const acceptedFileTypes = computed(() => {
  if (!supportedFileTypes.value.length) {
    return ''
  }
  const exts = new Set(supportedFileTypes.value)
  if (!isMemeries.value) {
    exts.add('.zip')
  }
  return Array.from(exts).join(',')
})

const uploadHint = computed(() => {
  if (!supportedFileTypes.value.length) {
    return '加载中...'
  }
  const exts = new Set(supportedFileTypes.value)
  if (!isMemeries.value) {
    exts.add('.zip')
  }
  return Array.from(exts).join(', ')
})

const isSupportedExtension = (fileName) => {
  if (!fileName) {
    return true
  }
  if (!supportedFileTypes.value.length) {
    return true
  }
  const lastDotIndex = fileName.lastIndexOf('.')
  if (lastDotIndex === -1) {
    return false
  }
  const ext = fileName.slice(lastDotIndex).toLowerCase()
  if (!isMemeries.value && ext === '.zip') return true
  return supportedFileTypes.value.includes(ext)
}

const loadSupportedFileTypes = async () => {
  // memeries 类型知识库使用媒体文件格式
  if (kbType.value === 'memeries') {
    applySupportedFileTypes(MEDIA_SUPPORTED_TYPES)
    return
  }
  try {
    const data = await fileApi.getSupportedFileTypes()
    applySupportedFileTypes(data?.file_types)
  } catch (error) {
    console.error('获取支持的文件类型失败:', error)
    message.warning('获取支持的文件类型失败，已使用默认配置')
    applySupportedFileTypes(DEFAULT_SUPPORTED_TYPES)
  }
}

const visible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const databaseId = computed(() => store.databaseId)
const kbType = computed(() => store.database.kb_type)

onMounted(() => {
  loadSupportedFileTypes()
})

// kbType 可能在 onMounted 之后才从 store 加载完成，需要 watch 重新设置
watch(kbType, () => {
  loadSupportedFileTypes()
})
const chunkLoading = computed(() => store.state.chunkLoading)

// 上传模式
const uploadMode = ref('file')
const previousOcrSelection = ref('disable')

const uploadModeOptions = computed(() => [
  {
    value: 'file',
    label: h('div', { class: 'segmented-option' }, [
      h(FileUp, { size: 16, class: 'option-icon' }),
      h('span', { class: 'option-text' }, '上传文件')
    ])
  },
  {
    value: 'folder',
    label: h('div', { class: 'segmented-option' }, [
      h(FolderUp, { size: 16, class: 'option-icon' }),
      h('span', { class: 'option-text' }, '上传文件夹')
    ])
  }
])

watch(uploadMode, (val) => {
  isFolderUpload.value = val === 'folder'
  // 切换模式时清空已选文件，避免混淆
  fileList.value = []
  sameNameFiles.value = []
})

// 文件列表
const fileList = ref([])

// 同名文件列表（用于显示提示）
const sameNameFiles = ref([])

// URL相关功能已移除

// OCR服务健康状态
const ocrHealthStatus = ref({
  onnx_rapid_ocr: { status: 'unknown', message: '' },
  mineru_ocr: { status: 'unknown', message: '' },
  mineru_official: { status: 'unknown', message: '' },
  paddlex_ocr: { status: 'unknown', message: '' },
  deepseek_ocr: { status: 'unknown', message: '' }
})

// OCR健康检查状态
const ocrHealthChecking = ref(false)

// 分块参数
const chunkParams = ref({
  enable_ocr: 'disable'
})

// 自动入库相关
const autoIndex = ref(false)
const indexParams = ref({
  chunk_size: 1000,
  chunk_overlap: 200,
  qa_separator: ''
})

// 计算属性：是否支持QA分割
const isQaSplitSupported = computed(() => {
  const type = kbType.value?.toLowerCase()
  return type === 'milvus'
})

const isGraphBased = computed(() => {
  const type = kbType.value?.toLowerCase()
  return type === 'lightrag'
})

const isMemeries = computed(() => {
  return kbType.value === 'memeries'
})

const isFolderUpload = ref(false)

// 计算属性：是否启用了OCR
const isOcrEnabled = computed(() => {
  return chunkParams.value.enable_ocr !== 'disable'
})

// 上传模式切换相关逻辑已移除

// 计算属性：是否有PDF或图片文件
const hasPdfOrImageFiles = computed(() => {
  if (fileList.value.length === 0) {
    return false
  }

  const pdfExtensions = ['.pdf']
  const imageExtensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.webp']
  const ocrExtensions = [...pdfExtensions, ...imageExtensions]

  return fileList.value.some((file) => {
    if (file.status !== 'done') {
      return false
    }

    const filePath = file.response?.file_path || file.name
    if (!filePath) {
      return false
    }

    const ext = filePath.substring(filePath.lastIndexOf('.')).toLowerCase()
    return ocrExtensions.includes(ext)
  })
})

// 计算属性：是否有ZIP文件
const hasZipFiles = computed(() => {
  if (fileList.value.length === 0) {
    return false
  }

  return fileList.value.some((file) => {
    if (file.status !== 'done') {
      return false
    }

    const filePath = file.response?.file_path || file.name
    if (!filePath) {
      return false
    }

    const ext = filePath.substring(filePath.lastIndexOf('.')).toLowerCase()
    return ext === '.zip'
  })
})

// 计算属性：OCR选项
const enableOcrOptions = computed(() => [
  {
    value: 'disable',
    label: '不启用',
    title: '不启用'
  },
  {
    value: 'onnx_rapid_ocr',
    label: getRapidOcrLabel(),
    title: 'ONNX with RapidOCR',
    disabled:
      ocrHealthStatus.value?.onnx_rapid_ocr?.status === 'unavailable' ||
      ocrHealthStatus.value?.onnx_rapid_ocr?.status === 'error'
  },
  {
    value: 'mineru_ocr',
    label: getMinerULabel(),
    title: 'MinerU OCR',
    disabled:
      ocrHealthStatus.value?.mineru_ocr?.status === 'unavailable' ||
      ocrHealthStatus.value?.mineru_ocr?.status === 'error'
  },
  {
    value: 'mineru_official',
    label: getMinerUOfficialLabel(),
    title: 'MinerU Official API',
    disabled:
      ocrHealthStatus.value?.mineru_official?.status === 'unavailable' ||
      ocrHealthStatus.value?.mineru_official?.status === 'error'
  },
  {
    value: 'paddlex_ocr',
    label: getPaddleXLabel(),
    title: 'PP-StructureV3',
    disabled:
      ocrHealthStatus.value?.paddlex_ocr?.status === 'unavailable' ||
      ocrHealthStatus.value?.paddlex_ocr?.status === 'error'
  },
  {
    value: 'deepseek_ocr',
    label: getDeepSeekOcrLabel(),
    title: 'DeepSeek OCR (SiliconFlow)',
    disabled:
      ocrHealthStatus.value?.deepseek_ocr?.status === 'unavailable' ||
      ocrHealthStatus.value?.deepseek_ocr?.status === 'error'
  }
])

// 获取当前选中OCR服务的状态
const selectedOcrStatus = computed(() => {
  switch (chunkParams.value.enable_ocr) {
    case 'onnx_rapid_ocr':
      return ocrHealthStatus.value?.onnx_rapid_ocr?.status || 'unknown'
    case 'mineru_ocr':
      return ocrHealthStatus.value?.mineru_ocr?.status || 'unknown'
    case 'mineru_official':
      return ocrHealthStatus.value?.mineru_official?.status || 'unknown'
    case 'paddlex_ocr':
      return ocrHealthStatus.value?.paddlex_ocr?.status || 'unknown'
    case 'deepseek_ocr':
      return ocrHealthStatus.value?.deepseek_ocr?.status || 'unknown'
    default:
      return null
  }
})

// 获取当前选中OCR服务的状态消息
const selectedOcrMessage = computed(() => {
  switch (chunkParams.value.enable_ocr) {
    case 'onnx_rapid_ocr':
      return ocrHealthStatus.value?.onnx_rapid_ocr?.message || ''
    case 'mineru_ocr':
      return ocrHealthStatus.value?.mineru_ocr?.message || ''
    case 'mineru_official':
      return ocrHealthStatus.value?.mineru_official?.message || ''
    case 'paddlex_ocr':
      return ocrHealthStatus.value?.paddlex_ocr?.message || ''
    case 'deepseek_ocr':
      return ocrHealthStatus.value?.deepseek_ocr?.message || ''
    default:
      return ''
  }
})

// OCR服务状态图标映射
const STATUS_ICONS = {
  healthy: '✅',
  unavailable: '❌',
  unhealthy: '⚠️',
  timeout: '⏰',
  error: '⚠️',
  unknown: '❓'
}

// OCR选项标签生成通用函数
const getOcrLabel = (serviceKey, displayName) => {
  const status = ocrHealthStatus.value?.[serviceKey]?.status || 'unknown'
  return `${STATUS_ICONS[status] || '❓'} ${displayName}`
}

// 兼容性包装器
const getRapidOcrLabel = () => getOcrLabel('onnx_rapid_ocr', 'RapidOCR (ONNX)')
const getMinerULabel = () => getOcrLabel('mineru_ocr', 'MinerU OCR')
const getMinerUOfficialLabel = () => getOcrLabel('mineru_official', 'MinerU Official API')
const getPaddleXLabel = () => getOcrLabel('paddlex_ocr', 'PP-StructureV3')
const getDeepSeekOcrLabel = () => getOcrLabel('deepseek_ocr', 'DeepSeek OCR')

// 验证OCR服务可用性
const validateOcrService = () => {
  if (chunkParams.value.enable_ocr === 'disable') {
    return true
  }

  const status = selectedOcrStatus.value
  if (status === 'unavailable' || status === 'error') {
    const ocrMessage = selectedOcrMessage.value
    message.error(`OCR服务不可用: ${ocrMessage}`)
    return false
  }

  return true
}

const handleCancel = () => {
  emit('update:visible', false)
}

const beforeUpload = (file) => {
  if (!isSupportedExtension(file?.name)) {
    message.error(`不支持的文件类型：${file?.name || '未知文件'}`)
    return Upload.LIST_IGNORE
  }
  return true
}

const formatFileSize = (bytes) => {
  if (bytes === 0 || !bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`
}

const formatFileTime = (timestamp) => {
  if (!timestamp) return ''
  try {
    const date = new Date(timestamp)
    return date.toLocaleString()
  } catch (e) {
    return timestamp
  }
}

const showSameNameFilesInUploadArea = (files) => {
  sameNameFiles.value = files
  // 可以在这里添加其他逻辑，比如自动滚动到提示区域
}

const downloadSameNameFile = async (file) => {
  try {
    // 获取当前数据库ID
    const currentDbId = databaseId.value
    if (!currentDbId) {
      message.error('知识库ID不存在')
      return
    }

    message.loading('正在下载文件...', 0)
    const response = await documentApi.downloadDocument(currentDbId, file.file_id)
    message.destroy()

    // 创建下载链接
    const blob = await response.blob() // 从 Response 对象中提取 Blob 数据
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = file.filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    message.success(`文件 ${file.filename} 下载成功`)
  } catch (error) {
    message.destroy()
    console.error('下载文件失败:', error)
    message.error(`下载文件失败: ${error.message || '未知错误'}`)
  }
}

const deleteSameNameFile = (file) => {
  Modal.confirm({
    title: '确认删除文件',
    content: `确定要删除文件 "${file.filename}" 吗？此操作不可恢复。`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        // 获取当前数据库ID
        const currentDbId = databaseId.value
        if (!currentDbId) {
          message.error('知识库ID不存在')
          return
        }

        message.loading('正在删除文件...', 0)
        await documentApi.deleteDocument(currentDbId, file.file_id)
        message.destroy()

        // 从同名文件列表中移除
        sameNameFiles.value = sameNameFiles.value.filter((f) => f.file_id !== file.file_id)

        message.success(`文件 ${file.filename} 删除成功`)
      } catch (error) {
        message.destroy()
        console.error('删除文件失败:', error)
        message.error(`删除文件失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

const customRequest = async (options) => {
  const { file, onProgress, onSuccess, onError } = options

  const formData = new FormData()
  // 如果是文件夹上传，使用相对路径作为文件名
  const filename =
    isFolderUpload.value && file.webkitRelativePath ? file.webkitRelativePath : file.name
  formData.append('file', file, filename)

  const dbId = databaseId.value
  if (!dbId) {
    onError(new Error('Database ID is missing'))
    return
  }

  const xhr = new XMLHttpRequest()
  xhr.open('POST', `/api/knowledge/files/upload?db_id=${dbId}`)

  const headers = getAuthHeaders()
  for (const [key, value] of Object.entries(headers)) {
    xhr.setRequestHeader(key, value)
  }

  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable) {
      onProgress({ percent: (e.loaded / e.total) * 100 })
    }
  }

  xhr.onload = () => {
    if (xhr.status >= 200 && xhr.status < 300) {
      try {
        const response = JSON.parse(xhr.responseText)
        onSuccess(response, xhr)
      } catch (e) {
        onError(e)
      }
    } else {
      const errorResp = JSON.parse(xhr.responseText)
      // 设置 file.response 让 handleFileUpload 能读取到错误信息
      file.response = errorResp
      const error = new Error(errorResp.detail || 'Upload failed')
      onError(error, file)
    }
  }

  xhr.onerror = (e) => {
    onError(e)
  }

  xhr.send(formData)
}

const handleFileUpload = (info) => {
  if (info?.file?.status === 'error') {
    const file = info.file
    // 尝试多种方式获取错误信息
    const detail = file?.response?.detail || file?.error?.message || ''
    if (detail.includes('same content') || detail.includes('相同内容')) {
      message.error(`${file.name} 已是相同内容文件，无需重复上传`)
    } else {
      message.error(detail || `文件上传失败：${file.name}`)
    }
  }

  // 检查是否有同名文件提示
  if (info?.file?.status === 'done' && info.file.response) {
    const response = info.file.response
    if (response.has_same_name && response.same_name_files && response.same_name_files.length > 0) {
      showSameNameFilesInUploadArea(response.same_name_files)
    }
  }

  fileList.value = info?.fileList ?? []
}

const handleDrop = () => {}

// 已移除文件夹上传逻辑

const checkOcrHealth = async () => {
  if (ocrHealthChecking.value) return

  ocrHealthChecking.value = true
  try {
    const healthData = await ocrApi.getHealth()
    ocrHealthStatus.value = healthData.services
  } catch (error) {
    console.error('OCR健康检查失败:', error)
    message.error('OCR服务健康检查失败')
  } finally {
    ocrHealthChecking.value = false
  }
}

const getAuthHeaders = () => {
  const userStore = useUserStore()
  return userStore.getAuthHeaders()
}

const openDocLink = () => {
  // 移除外部文档链接
  message.info('请联系管理员获取文档处理帮助')
}

const chunkData = async () => {
  if (!databaseId.value) {
    message.error('请先选择知识库')
    return
  }

  // 验证OCR服务可用性
  if (!validateOcrService()) {
    return
  }

  const imageExtensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']

  // 提取已上传的文件信息
  const items = []
  const content_hashes = {}
  for (const file of fileList.value) {
    if (file.status !== 'done') continue
    const file_path = file.response?.file_path
    const content_hash = file.response?.content_hash
    if (!file_path) continue

    items.push(file_path)
    if (content_hash) content_hashes[file_path] = content_hash

    // 检查是否需要OCR
    const ext = file_path.substring(file_path.lastIndexOf('.')).toLowerCase()
    if (imageExtensions.includes(ext) && chunkParams.value.enable_ocr === 'disable') {
      message.error({
        content: '检测到图片文件，必须启用 OCR 才能提取文本内容。',
        duration: 5
      })
      return
    }
  }

  if (items.length === 0) {
    message.error('请先上传文件')
    return
  }

  try {
    store.state.chunkLoading = true
    const params = { ...chunkParams.value, content_hashes }
    if (autoIndex.value) {
      params.auto_index = true
      Object.assign(params, indexParams.value)
    }

    await store.addFiles({
      items,
      contentType: 'file',
      params,
      parentId: selectedFolderId.value
    })

    emit('success')
    handleCancel()
    fileList.value = []
    sameNameFiles.value = []
  } catch (error) {
    console.error('文件上传失败:', error)
    message.error('文件上传失败: ' + (error.message || '未知错误'))
  } finally {
    store.state.chunkLoading = false
  }
}
</script>

<style lang="less" scoped>
.footer-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.footer-buttons {
  display: flex;
  gap: 8px;
}

.add-files-content {
  padding: 8px 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* Top Bar */
.top-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.help-link-btn {
  color: var(--gray-600);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;

  &:hover {
    color: var(--main-color);
  }
}

.custom-segmented {
  background-color: var(--gray-100);
  padding: 3px;

  .segmented-option {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 32px;
    .option-text {
      margin-left: 6px;
    }
  }
}

/* Settings Panel */
.settings-panel {
  background-color: var(--gray-50);
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.setting-row {
  display: flex;
  flex-direction: column;
  gap: 8px;

  &.two-cols {
    flex-direction: row;
    gap: 20px;
  }

  .col-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
    min-width: 0; // Fix flex overflow
  }
}

.setting-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--gray-700);
  display: flex;
  align-items: center;
  gap: 8px;
}

.action-icon {
  color: var(--gray-400);
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    color: var(--main-color);
  }

  &.spinning {
    animation: spin 1s linear infinite;
    color: var(--main-color);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.flex-row {
  display: flex;
  align-items: center;
  width: 100%;
}

.folder-select {
  flex: 1;
}

.folder-checkbox {
  margin-left: 12px;
  white-space: nowrap;
}

.param-description {
  font-size: 12px;
  color: var(--gray-400);
  margin: 4px 0 0 0;
  line-height: 1.4;
  display: flex;
  align-items: center;
  gap: 4px;

  .text-success {
    color: var(--color-success-500);
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .text-warning {
    color: var(--color-warning-500);
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

/* Chunk Display Card */
.chunk-display-card {
  background: var(--gray-0);
  border: 1px solid var(--gray-300);
  border-radius: 6px;
  padding: 0 12px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--main-color);
    box-shadow: 0 0 0 2px var(--main-100);

    .edit-icon {
      color: var(--main-color);
    }
  }

  &.disabled {
    background: var(--gray-100);
    cursor: not-allowed;
    color: var(--gray-400);
    &:hover {
      border-color: var(--gray-300);
      box-shadow: none;
    }
  }
}

.chunk-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--gray-700);

  .divider {
    color: var(--gray-300);
    font-size: 10px;
  }

  b {
    font-weight: 600;
    color: var(--gray-900);
  }
}

.edit-icon {
  color: var(--gray-400);
  font-size: 14px;
}

/* Alerts */
.inline-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 13px;

  &.warning {
    background: var(--color-warning-50);
    border: 1px solid var(--color-warning-200);
    color: var(--color-warning-700);
  }
}

/* Upload Area */
.upload-area {
  flex: 1;
}

.custom-dragger {
  :deep(.ant-upload-drag) {
    background: var(--gray-0);
    border-radius: 8px;
    border: 1px dashed var(--gray-300);
    transition: all 0.3s;

    &:hover {
      border-color: var(--main-color);
      background: var(--main-50);
    }
  }

  .ant-upload-drag-icon {
    font-size: 32px;
    color: var(--main-300);
    margin-bottom: 8px;
  }

  .ant-upload-text {
    font-size: 15px;
    color: var(--gray-800);
    margin-bottom: 4px;
  }

  .ant-upload-hint {
    font-size: 12px;
    color: var(--gray-500);
  }
}

.zip-tip {
  margin-top: 8px;
  font-size: 12px;
  color: var(--color-warning-600);
  background: var(--color-warning-50);
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
}

/* Conflict Files Panel */
.conflict-files-panel {
  border: 1px solid var(--gray-200);
  border-radius: 8px;
  overflow: hidden;
  background: var(--gray-0);
  margin-top: 4px;
}

.panel-header {
  background: var(--gray-50);
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 500;
  color: var(--gray-700);
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid var(--gray-200);

  .icon-warning {
    color: var(--color-warning-500);
  }
}

.file-list-scroll {
  max-height: 120px;
  overflow-y: auto;
}

.conflict-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-bottom: 1px solid var(--gray-100);
  transition: background 0.2s;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background: var(--gray-50);
  }
}

.file-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
  font-size: 13px;

  .fname {
    font-weight: 500;
    color: var(--gray-800);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .ftime {
    color: var(--gray-400);
    font-size: 12px;
    flex-shrink: 0;
  }
}

.file-actions {
  display: flex;
  gap: 4px;

  .action-btn {
    color: var(--gray-500);

    &:hover {
      color: var(--main-600);
      background: var(--main-50);
    }

    &.delete:hover {
      color: var(--color-error-500);
      background: var(--color-error-50);
    }
  }
}

.auto-index-params {
  margin-top: 8px;
  padding: 12px;
  background: var(--gray-0);
  border: 1px solid var(--gray-200);
  border-radius: 6px;
}

.lightrag-tip {
  display: flex;
  align-items: center;
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--main-50);
  border-radius: 6px;
  font-size: 13px;
  color: var(--gray-600);
}

.setting-label .ant-checkbox {
  margin-right: 8px;
}
</style>
