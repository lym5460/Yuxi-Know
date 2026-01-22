import { fileURLToPath, URL } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// 虚拟模块插件 - 提供 WebGPURenderer 的 stub
function webgpuStubPlugin() {
  const virtualModuleId = 'three/webgpu'
  const resolvedVirtualModuleId = '\0' + virtualModuleId

  return {
    name: 'webgpu-stub',
    resolveId(id) {
      if (id === virtualModuleId) {
        return resolvedVirtualModuleId
      }
    },
    load(id) {
      if (id === resolvedVirtualModuleId) {
        // 返回一个空的 WebGPURenderer stub
        return `export class WebGPURenderer {}`
      }
    }
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [vue(), webgpuStubPlugin()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      proxy: {
        '^/api': {
          target: env.VITE_API_URL || 'http://api:5050',
          changeOrigin: true
        }
      },
      watch: {
        usePolling: true,
        ignored: ['**/node_modules/**', '**/dist/**'],
      },
      host: '0.0.0.0',
    },
    build: {
      // 优化生产构建，解决 3d-force-graph 和 three.js 的兼容性问题
      rollupOptions: {
        output: {
          manualChunks: {
            // 将 three.js 相关库单独打包
            'three-vendor': ['three', 'three-spritetext'],
            // 将 3d-force-graph 单独打包
            '3d-graph': ['3d-force-graph'],
            // 将其他大型库分离
            'graph-vendor': ['graphology', 'sigma', 'd3'],
            'ui-vendor': ['ant-design-vue', '@ant-design/icons-vue']
          }
        }
      },
      // 增加 chunk 大小警告阈值
      chunkSizeWarningLimit: 1000,
      // 确保正确处理 CommonJS 模块
      commonjsOptions: {
        include: [/node_modules/],
        transformMixedEsModules: true
      }
    },
    optimizeDeps: {
      // 预构建优化，确保 three.js 和相关库正确处理
      include: [
        'three',
        'three-spritetext',
        '3d-force-graph',
        'graphology',
        'sigma',
        'd3'
      ],
      // 排除有问题的模块，让 Vite 直接处理
      exclude: []
    }
  }
})
