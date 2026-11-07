import { fileURLToPath, URL } from 'node:url'

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// 开发期把 /api 代理到 FastAPI（8010），前端不用管 CORS 和端口。
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8010', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8010', changeOrigin: true },
    },
    // 编辑器的"原子写"会在同目录留下 .xxx.tmpdir 临时目录，chokidar 去监听它
    // 在 Windows 上会 EBUSY 把 dev server 打挂，直接忽略。
    watch: { ignored: ['**/node_modules/**', '**/dist/**', '**/*.tmpdir/**'] },
  },
})
