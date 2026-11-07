/**
 * 本机会话索引。
 *
 * 为什么要这一层：后端的 checkpoint 里只存状态，不存"最近聊过哪些会话"，
 * 而演示时需要一条能点回去的列表（尤其"停在审批闸门"那条）。
 * 所以这里维护一份轻量索引（thread_id / 首句标题 / 状态点），落 localStorage。
 */

import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type SessionState = 'idle' | 'running' | 'paused' | 'done'

export interface SessionItem {
  threadId: string
  title: string
  state: SessionState
  updatedAt: number
}

const STORAGE_KEY = 'smartdesk.sessions'
const MAX_ITEMS = 12

/** thread_id 的格式跟着后端约定走：web-YYYYMMDDHHmmss-xxxx，方便一眼看出是网页端发起的。 */
export function newThreadId(): string {
  return `web-${new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '')}-${Math.random()
    .toString(36)
    .slice(2, 6)}`
}

function load(): SessionItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? (JSON.parse(raw) as SessionItem[]) : []
    if (Array.isArray(parsed)) return parsed.filter((item) => item?.threadId).slice(0, MAX_ITEMS)
  } catch {
    /* 本地存储坏了就当没有历史 */
  }
  return []
}

export const useSessions = defineStore('sessions', () => {
  const items = ref<SessionItem[]>(load())
  const current = ref<string>(items.value[0]?.threadId ?? '')

  watch(
    items,
    (value) => localStorage.setItem(STORAGE_KEY, JSON.stringify(value.slice(0, MAX_ITEMS))),
    { deep: true },
  )

  function find(threadId: string) {
    return items.value.find((item) => item.threadId === threadId)
  }

  /** 开一条新会话并切过去（标题等第一条用户消息再补）。 */
  function start(): string {
    const threadId = newThreadId()
    items.value = [
      { threadId, title: '新会话', state: 'idle' as SessionState, updatedAt: Date.now() },
      ...items.value,
    ].slice(0, MAX_ITEMS)
    current.value = threadId
    return threadId
  }

  /** 确保有当前会话（首次进页面时用）。 */
  function ensure(): string {
    if (!current.value || !find(current.value)) return start()
    return current.value
  }

  function select(threadId: string) {
    if (find(threadId)) current.value = threadId
  }

  /** 接住"别人发给我的会话链接"：本地没有就补一条再切过去（?thread=xxx 用）。 */
  function adopt(threadId: string) {
    if (!find(threadId)) {
      items.value = [{ threadId, title: threadId, state: 'idle', updatedAt: Date.now() } as SessionItem, ...items.value].slice(
        0,
        MAX_ITEMS,
      )
    }
    current.value = threadId
  }

  function update(threadId: string, patch: Partial<Omit<SessionItem, 'threadId'>>) {
    const item = find(threadId)
    if (!item) return
    Object.assign(item, patch, { updatedAt: Date.now() })
  }

  /** 第一条用户消息决定标题；已经有真标题就不再覆盖。 */
  function titleFrom(threadId: string, text: string) {
    const item = find(threadId)
    if (!item || (item.title !== '新会话' && item.title !== '')) return
    item.title = text.replace(/\s+/g, ' ').slice(0, 22)
    item.updatedAt = Date.now()
  }

  function remove(threadId: string) {
    items.value = items.value.filter((item) => item.threadId !== threadId)
    if (current.value === threadId) current.value = items.value[0]?.threadId ?? ''
  }

  return { items, current, start, ensure, select, adopt, update, titleFrom, remove }
})
