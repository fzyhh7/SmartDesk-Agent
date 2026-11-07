<script setup lang="ts">
/**
 * 左栏：品牌 + 会话搜索 + 三个页面入口 + 本机会话列表 + 底部身份卡。
 *
 * 会话列表是"本地索引"（见 stores/sessions.ts）：点一条就是把聊天页指向那个 thread_id，
 * 页面会去 GET /runs/{thread_id} 把闸门卡片和状态重新画出来。
 */

import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import IdentityCard from '@/components/IdentityCard.vue'
import { useSessions, type SessionItem } from '@/stores/sessions'
import { useUi } from '@/stores/ui'
import { relTime } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const sessions = useSessions()
const ui = useUi()

const filter = ref('')

const NAV = [
  { path: '/chat', label: '会话工作台', icon: 'chat' },
  { path: '/approvals', label: '审批中心', icon: 'shield', badge: true },
  { path: '/tickets', label: '工单看板', icon: 'ticket' },
]

const STATE_TEXT: Record<string, string> = {
  idle: '空闲',
  running: '进行中',
  paused: '停在闸门',
  done: '已完成',
}

const filtered = computed(() => {
  const keyword = filter.value.trim().toLowerCase()
  const items = sessions.items
  if (!keyword) return items
  return items.filter(
    (item) => item.title.toLowerCase().includes(keyword) || item.threadId.toLowerCase().includes(keyword),
  )
})

function dotClass(item: SessionItem) {
  if (item.state === 'paused') return 'warn'
  if (item.state === 'running') return 'warn'
  if (item.state === 'done') return 'ok'
  return ''
}

function go(path: string) {
  if (route.path !== path) void router.push(path)
}

function openSession(item: SessionItem) {
  sessions.select(item.threadId)
  go('/chat')
}

function newSession() {
  sessions.start()
  go('/chat')
}
</script>

<template>
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-mark"><AppIcon name="spark" :size="17" /></div>
      <div class="brand-text">
        <div class="brand-name">SmartDesk-Agent</div>
        <div class="brand-sub">企业服务台 Agent</div>
      </div>
    </div>

    <label class="cmdk">
      <AppIcon name="search" :size="14" />
      <input v-model="filter" placeholder="搜索会话 / 单号" spellcheck="false" />
      <kbd>⌘K</kbd>
    </label>

    <nav class="nav">
      <div class="nav-label">工作区</div>
      <button
        v-for="item in NAV"
        :key="item.path"
        type="button"
        class="nav-item"
        :class="{ active: route.path === item.path }"
        @click="go(item.path)"
      >
        <AppIcon :name="item.icon" :size="16" />
        <span>{{ item.label }}</span>
        <span v-if="item.badge && ui.pending > 0" class="count">{{ ui.pending }}</span>
      </button>
    </nav>

    <div class="sessions">
      <div class="nav-label">本机会话</div>
      <button
        v-for="item in filtered"
        :key="item.threadId"
        type="button"
        class="session"
        :class="{ active: item.threadId === sessions.current }"
        @click="openSession(item)"
      >
        <span class="dot" :class="dotClass(item)" />
        <span class="body">
          <span class="t">{{ item.title }}</span>
          <span class="meta">{{ STATE_TEXT[item.state] ?? item.state }} · {{ relTime(item.updatedAt) }}</span>
        </span>
      </button>

      <button type="button" class="session new" @click="newSession">
        <AppIcon name="plus" :size="13" />
        <span class="t">新会话</span>
      </button>
    </div>

    <div class="side-foot">
      <IdentityCard />
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 238px;
  flex: none;
  background: var(--paper);
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 17px 16px 13px;
}
.brand-mark {
  width: 31px;
  height: 31px;
  border-radius: 9px;
  flex: none;
  color: #fff;
  display: grid;
  place-items: center;
  background: linear-gradient(145deg, #5b74ea, #3a56d4 58%, #2c43ad);
  box-shadow: 0 2px 8px rgba(58, 86, 212, 0.32), inset 0 1px 0 rgba(255, 255, 255, 0.24);
}
.brand-name {
  font-size: 13.6px;
  font-weight: 700;
  letter-spacing: -0.015em;
  line-height: 1.25;
}
.brand-sub {
  font-size: 10.4px;
  color: var(--ink-4);
  margin-top: 1px;
}

.cmdk {
  margin: 0 12px 10px;
  display: flex;
  align-items: center;
  gap: 7px;
  height: 30px;
  padding: 0 9px;
  border: 1px solid var(--line);
  border-radius: 9px;
  background: var(--paper-2);
  color: var(--ink-4);
  cursor: text;
}
.cmdk:focus-within {
  border-color: #a9b7f2;
  box-shadow: 0 0 0 3px rgba(58, 86, 212, 0.09);
}
.cmdk input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  font: inherit;
  font-size: 12px;
  color: var(--ink);
}
.cmdk input::placeholder {
  color: var(--ink-4);
}

.nav {
  padding: 0 10px;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.nav-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--ink-4);
  padding: 13px 8px 6px;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 7.5px 9px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--ink-2);
  font: inherit;
  font-size: 12.8px;
  text-align: left;
  cursor: pointer;
  transition: background 0.13s, color 0.13s;
}
.nav-item:hover {
  background: var(--paper-2);
  color: var(--ink);
}
.nav-item.active {
  background: var(--brand-tint);
  color: var(--brand);
  font-weight: 640;
}
.nav-item .count {
  margin-left: auto;
  font-size: 10.4px;
  font-weight: 700;
  line-height: 1.55;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--bad-tint);
  color: var(--bad);
}

.sessions {
  padding: 0 10px;
  overflow-y: auto;
  min-height: 0;
  flex: 1;
}
.session {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  width: 100%;
  padding: 7.5px 9px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--ink-2);
  font: inherit;
  font-size: 12.2px;
  line-height: 1.42;
  text-align: left;
  cursor: pointer;
  transition: background 0.12s;
}
.session:hover {
  background: var(--paper-2);
}
.session.active {
  background: var(--paper-2);
  box-shadow: inset 0 0 0 1px var(--line-2);
}
.session .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-top: 5.5px;
  flex: none;
  background: var(--ink-4);
  box-shadow: 0 0 0 3px rgba(154, 161, 177, 0.12);
}
.session .dot.ok {
  background: #18a05a;
  box-shadow: 0 0 0 3px rgba(24, 160, 90, 0.13);
}
.session .dot.warn {
  background: #d98613;
  box-shadow: 0 0 0 3px rgba(217, 134, 19, 0.15);
}
.session .body {
  min-width: 0;
  flex: 1;
}
.session .t {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.session .meta {
  display: block;
  font-size: 10.4px;
  color: var(--ink-4);
  margin-top: 2px;
}
.session.new {
  color: var(--brand);
  font-weight: 640;
  align-items: center;
  padding: 8px 9px;
}

.side-foot {
  border-top: 1px solid var(--line);
  padding: 10px;
}
</style>
