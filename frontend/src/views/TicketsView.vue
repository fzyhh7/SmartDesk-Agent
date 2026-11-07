<script setup lang="ts">
/**
 * 工单看板。
 *
 * 这里刻意用自绘表格而不是 el-table：只有 7 列、要的是"扫一眼"的密度，
 * 自绘能把行高压到 44px、把状态做成语义色徽章，比默认表格更像产品而不是后台。
 *
 * 过滤是两层的：`我的工单` 只是界面上少看几行，真正的租户/归属过滤在 MCP 服务端
 * （`guard.can_read_ticket`），前端不做安全边界。
 */

import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import { api } from '@/api/client'
import { useIdentity } from '@/stores/identity'
import { useUi } from '@/stores/ui'
import { clock, relTime, ticketStatus, urgencyMeta } from '@/utils/format'
import { avatarText, displayName } from '@/utils/people'
import type { TicketRow } from '@/types'

const identity = useIdentity()
const ui = useUi()
const router = useRouter()

const rows = ref<TicketRow[]>([])
const loading = ref(false)
const message = ref('')
const keyword = ref('')
const scope = ref<'all' | 'open' | 'in_progress' | 'closed'>('all')
const mineOnly = ref(false)
/** 读失败 / 上次读成功的时间：决定内容区中间显示"读失败"还是"真的没有"。 */
const failed = ref(false)
const updatedAt = ref<string>('')

const SCOPES = [
  { key: 'all', label: '全部' },
  { key: 'open', label: '待处理' },
  { key: 'in_progress', label: '处理中' },
  { key: 'closed', label: '已关闭' },
] as const

const scoped = computed(() => {
  let list = rows.value
  if (mineOnly.value) list = list.filter((row) => row.reporter === identity.userId)
  if (scope.value !== 'all') list = list.filter((row) => row.status === scope.value)
  const word = keyword.value.trim().toLowerCase()
  if (word) {
    list = list.filter(
      (row) =>
        row.ticket_no.toLowerCase().includes(word) ||
        row.title.toLowerCase().includes(word) ||
        row.reporter.toLowerCase().includes(word),
    )
  }
  return list
})

function countOf(key: string): number {
  const base = mineOnly.value ? rows.value.filter((row) => row.reporter === identity.userId) : rows.value
  if (key === 'all') return base.length
  return base.filter((row) => row.status === key).length
}

async function load(silent = false) {
  if (!silent) loading.value = true
  message.value = ''
  try {
    // 后端 /tickets 的 limit 上限是 50（Query(le=50)），超了会 422
    const data = await api.tickets('', 50)
    rows.value = data.tickets ?? []
    failed.value = false
    updatedAt.value = new Date().toISOString()
  } catch (err) {
    failed.value = true
    message.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

/**
 * 表格区正中间那块大状态：只有"一条工单都没有"时才占位。
 * 已经有数据、只是被筛选条件过滤空了，走表格里那个小空态（带「看全部」）。
 */
const tableState = computed<'' | 'down' | 'error' | 'loading' | 'empty'>(() => {
  if (rows.value.length) return ''
  if (ui.healthy === false) return 'down'
  if (failed.value) return 'error'
  if (loading.value) return 'loading'
  return 'empty'
})

const tableTitle = computed(() => {
  switch (tableState.value) {
    case 'down':
      return '后端没连上'
    case 'error':
      return '读取失败'
    case 'loading':
      return '正在读取工单…'
    default:
      return '还没有任何工单'
  }
})

const tableText = computed(() => {
  switch (tableState.value) {
    case 'down':
      return '工单存在后端（ticket-server 的 SQLite）里，前端只是读它。后端起来之后这一页就会有内容。'
    case 'error':
      return message.value || '请求没有成功，点重试再来一次。'
    case 'loading':
      return '正在从 /api/v1/tickets 拉数据。'
    default:
      return '在聊天里说一句「帮我建个工单：…」，Agent 建完之后会出现在这里。'
  }
})

async function retry() {
  await ui.refreshHealth()
  await load()
}

function resetFilter() {
  scope.value = 'all'
  keyword.value = ''
  mineOnly.value = false
}

/** 别人正在建单时这一页不该停在旧数据上：切回窗口 + 每 30 秒静默刷新。 */
let timer: number | undefined

function onFocus() {
  if (document.visibilityState === 'visible') void load(true)
}

onMounted(() => {
  void load()
  timer = window.setInterval(() => {
    if (!loading.value && document.visibilityState === 'visible') void load(true)
  }, 30000)
  window.addEventListener('focus', onFocus)
})

onUnmounted(() => {
  if (timer) window.clearInterval(timer)
  window.removeEventListener('focus', onFocus)
})
</script>

<template>
  <div class="tickets">
    <div class="bar">
      <div class="seg">
        <button
          v-for="item in SCOPES"
          :key="item.key"
          type="button"
          class="seg-item"
          :class="{ on: scope === item.key }"
          @click="scope = item.key"
        >
          {{ item.label }}<span class="n">{{ countOf(item.key) }}</span>
        </button>
      </div>

      <label class="search">
        <AppIcon name="search" :size="13" />
        <input v-model="keyword" placeholder="搜单号 / 标题 / 提单人" spellcheck="false" />
      </label>

      <span class="spacer" />

      <button type="button" class="btn ghost sm" :class="{ on: mineOnly }" @click="mineOnly = !mineOnly">
        <AppIcon name="user" :size="13" /> 我的工单
      </button>
      <span class="upd">{{ updatedAt ? `最近更新 ${clock(updatedAt)}` : '' }}</span>
      <button type="button" class="btn ghost sm" :disabled="loading" @click="load()">
        <AppIcon name="refresh" :size="13" /> {{ loading ? '刷新中' : '刷新' }}
      </button>
      <button type="button" class="btn primary sm" @click="router.push('/chat')">
        <AppIcon name="plus" :size="13" /> 让 Agent 建单
      </button>
    </div>

    <p v-if="message && !tableState" class="banner">{{ message }}</p>

    <!-- 表格区正中间的大状态：一屏空白最容易被当成"没数据"或"页面坏了" -->
    <div v-if="tableState" class="state" :class="{ bad: tableState === 'down' || tableState === 'error' }">
      <div class="ico">
        <AppIcon :name="tableState === 'empty' ? 'ticket' : 'alert'" :size="20" />
      </div>
      <h3>{{ tableTitle }}</h3>
      <p>{{ tableText }}</p>
      <div v-if="tableState === 'loading'" class="skel">
        <i style="width: 82%" /><i style="width: 64%" /><i style="width: 74%" />
      </div>
      <template v-else>
        <div class="acts">
          <button type="button" class="btn primary sm" @click="retry">
            <AppIcon name="refresh" :size="13" />
            {{ tableState === 'down' ? '重试连接' : tableState === 'error' ? '重试' : '刷新一下' }}
          </button>
          <button v-if="tableState === 'empty'" type="button" class="btn ghost sm" @click="router.push('/chat')">
            <AppIcon name="plus" :size="13" /> 让 Agent 建一张
          </button>
        </div>
        <p v-if="tableState === 'down'" class="hint">
          启动后端：<code>python -m uvicorn backend.app.api.main:app --port 8010</code>
        </p>
      </template>
    </div>

    <div v-else class="panel table">
      <div class="tr th">
        <span>单号</span>
        <span>标题</span>
        <span>状态</span>
        <span>优先级</span>
        <span>分类</span>
        <span>提单人</span>
        <span class="right">创建时间</span>
      </div>

      <div v-for="row in scoped" :key="row.ticket_no" class="tr body-row">
        <span class="mono ticket-no">{{ row.ticket_no }}</span>
        <span class="cell-title">
          <span class="t">{{ row.title }}</span>
          <span class="d">{{ row.description || row.resolution || '—' }}</span>
        </span>
        <span>
          <span class="pill" :class="ticketStatus(row.status).tone">{{ ticketStatus(row.status).text }}</span>
        </span>
        <span class="urgency">
          <i class="urg-dot" :class="urgencyMeta(row.urgency).tone" />
          {{ urgencyMeta(row.urgency).text }}
        </span>
        <span class="dim">{{ row.category || '—' }}</span>
        <span class="reporter">
          <i class="ava">{{ avatarText(row.reporter) }}</i>
          {{ displayName(row.reporter) }}
        </span>
        <span class="right dim mono" :title="row.created_at">{{ clock(row.created_at) }}</span>
      </div>

      <div v-if="!scoped.length" class="empty">
        <div class="ico"><AppIcon name="filter" :size="17" /></div>
        <p>这个筛选条件下没有工单</p>
        <p class="sub">换个状态段，或者把搜索词清掉</p>
        <button type="button" class="btn ghost sm" @click="resetFilter">看全部</button>
      </div>

      <div class="table-foot">
        <span>{{ mineOnly ? '我的工单' : '员工只看自己提的单 · 主管看全租户（过滤在 MCP 服务端做，不靠前端藏）' }}</span>
        <span class="mono">共 {{ scoped.length }} 条 · 更新于 {{ relTime(rows[0]?.updated_at) || '—' }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tickets {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 18px 26px 26px;
}

.bar {
  display: flex;
  align-items: center;
  gap: 9px;
}
.spacer {
  flex: 1;
}
.upd {
  font-size: 10.6px;
  color: var(--ink-4);
  white-space: nowrap;
}
.btn.on {
  border-color: #b9c4f4;
  color: var(--brand);
  background: var(--brand-tint);
}

.search {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 10px;
  border: 1px solid var(--line-2);
  border-radius: 9px;
  background: var(--paper);
  color: var(--ink-4);
  min-width: 220px;
}
.search:focus-within {
  border-color: #a9b7f2;
  box-shadow: 0 0 0 3px rgba(58, 86, 212, 0.09);
}
.search input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  font: inherit;
  font-size: 12px;
  color: var(--ink);
}

.banner {
  margin: 10px 0 0;
  padding: 8px 11px;
  border-radius: var(--r-sm);
  background: var(--bad-tint);
  border: 1px solid var(--bad-line);
  color: #8d2216;
  font-size: 11.4px;
}

.table {
  margin-top: 12px;
  padding: 0;
  overflow: hidden;
}

.tr {
  display: grid;
  grid-template-columns: 142px minmax(0, 1fr) 92px 74px 92px 106px 84px;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
}
.th {
  height: 34px;
  border-bottom: 1px solid var(--line);
  background: var(--paper-2);
  font-size: 10.4px;
  font-weight: 660;
  color: var(--ink-4);
}
.body-row {
  min-height: 46px;
  padding-top: 7px;
  padding-bottom: 7px;
  border-bottom: 1px solid var(--line);
  transition: background 0.12s;
}
.body-row:hover {
  background: #fafbfe;
}
.body-row:last-of-type {
  border-bottom: 0;
}

.ticket-no {
  font-size: 10.8px;
  color: var(--ink-3);
}
.cell-title {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.cell-title .t {
  font-size: 12.2px;
  font-weight: 580;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cell-title .d {
  font-size: 10.2px;
  color: var(--ink-4);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.urgency {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.2px;
  color: var(--ink-2);
}
.urg-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--ink-4);
}
.urg-dot.bad {
  background: var(--bad);
}
.urg-dot.warn {
  background: #d98613;
}
.dim {
  font-size: 11px;
  color: var(--ink-3);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.reporter {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.4px;
  color: var(--ink-2);
}
.ava {
  width: 18px;
  height: 18px;
  flex: none;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 9.6px;
  font-style: normal;
  font-weight: 620;
  color: var(--brand);
  background: var(--brand-tint);
  border: 1px solid var(--brand-line);
}
.right {
  text-align: right;
  justify-self: end;
}

.table-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  height: 34px;
  padding: 0 14px;
  border-top: 1px solid var(--line);
  background: var(--paper-2);
  font-size: 10.2px;
  color: var(--ink-4);
}
</style>
