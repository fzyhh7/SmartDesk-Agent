import { createRouter, createWebHistory } from 'vue-router'

export const routes = [
  { path: '/', redirect: '/chat' },
  {
    path: '/chat',
    name: 'chat',
    component: () => import('@/views/ChatView.vue'),
    meta: { title: '会话工作台', sub: '新会话 · 直接问，或从下面的示例开始' },
  },
  {
    path: '/approvals',
    name: 'approvals',
    component: () => import('@/views/ApprovalView.vue'),
    meta: { title: '审批中心', sub: '待办来自 SQLite approvals 表 · 点通过会用 thread_id 恢复对应会话' },
  },
  {
    path: '/tickets',
    name: 'tickets',
    component: () => import('@/views/TicketsView.vue'),
    meta: { title: '工单看板', sub: '数据在 ticket-server 的 SQLite · 员工只看自己提的单' },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})
