import { Database, Waypoints, DatabaseZap, Video } from 'lucide-vue-next'

export const getKbTypeLabel = (type) => {
  const labels = {
    lightrag: 'LightRAG',
    milvus: 'CommonRAG',
    memeries: '媒体知识库',
    dify: 'Dify'
  }
  return labels[type] || type
}

export const getKbTypeIcon = (type) => {
  const icons = {
    lightrag: Waypoints,
    milvus: DatabaseZap,
    memeries: Video,
    dify: Database
  }
  return icons[type] || Database
}

export const getKbTypeColor = (type) => {
  const colors = {
    lightrag: 'purple',
    milvus: 'red',
    memeries: 'cyan',
    dify: 'gold'
  }
  return colors[type] || 'blue'
}
