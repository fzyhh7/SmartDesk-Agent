<script setup lang="ts">
/**
 * 审批中心：三列看板 + 右侧抽屉。
 *
 * 为什么是看板而不是表格：待办通常个位数，人关心的是"哪一列在积压"，
 * 而不是"第 7 行第 3 列的值"。决策需要的细节（为什么被拦、参数、审批链）
 * 放进抽屉，列表本身保持可扫视。
 *
 * 这里的每一条都对应 approvals 表的一行，`thread_id` 是能 resume 回那条会话的钥匙：
 * 点"通过"= 用发起人的那条 thread 调 /runs/{id}/resume，后端会按"当前恢复人"的身份二次鉴权。
 */

import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import { api } from '@/api/client'
import { resumeStream } from '@/api/sse'
import { useIdentity } from '@/stores/identity'
import { useUi } from '@/stores/ui'
import { clock, durationText, gateText, opLabel, relTime, riskMeta, toDate } from '@/utils/format'
import { displayName } from '@/utils/people'
import type { ApprovalRow } from '@/types'

const identity = useIdentity()
const ui = useUi()

const rows = ref<ApprovalRow[]>([])
const loading = ref(false)
const acting = ref<number | null>(null)
const message = ref('')
const active = ref<ApprovalRow | null>(null)
const route = useRoute()
const rejectReason = ref('')
/** 读失败 / 最近一次读成功的时间：决定内容区中间显示"读失败"还是"空的"。 */
const failed = ref(false)
const updatedAt = ref<string>('')

const pending = computed(() => rows.value.filter((row) => row.status === 'pending'))
const passed = computed(() => rows.value.filter((row) => row.status === 'approved' || row.status === 'edited'))
const rejected = computed(() => rows.value.filter((row) => row.status === 'rejected'))

/** 看板每列最多摆 10 张，剩下的用一行文字说明——历史记录会越攒越多，不该把 DOM 拉爆。 */
const LIMIT = 10
const pendingShown = computed(() => pending.value.slice(0, LIMIT))
const passedShown = computed(() => passed.value.slice(0, LIMIT))
const rejectedShown = computed(() => rejected.value.slice(0, LIMIT))

const todayPassed = computed(() => {
  const today = new Date().toDateString()
  return passed.value.filter((row) => toDate(row.decided_at)?.toDateString() === today).length
})

const avgStay = computed(() => {
  const done = rows.value.filter((row) => row.decided_at && row.created_at)
  if (!done.length) return '-'
  const total = done.reduce((sum, row) => {
    const from = toDate(row.created_at)
    const to = toDate(row.decided_at)
    if (!from || !to) return sum
    return sum + Math.max(0, to.getTime() - from.getTime())
  }, 0)
  const avg = total / done.length
  return durationText(new Date(Date.now() - avg).toISOString(), new Date().toISOString())
})

async function load(silent = false) {
  if (!silent) loading.value = true
  try {
    const data = await api.approvals('', 100)
    rows.value = data.approvals ?? []
    ui.setPending(pending.value.length)
    failed.value = false
    message.value = ''
    updatedAt.value = new Date().toISOString()
    // ?open=<id> 是"把这一条审批的链接发给主管"：加载完直接把抽屉拉到那条
    const wanted = typeof route.query.open === 'string' ? route.query.open : ''
    if (wanted) {
      const hit = rows.value.find((row) => String(row.id) === wanted)
      if (hit) active.value = hit
    }
  } catch (err) {
    failed.value = true
    message.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

/**
 * 内容区正中间那块大状态。
 * 只有"一行数据都没有"时才占位 —— 已经有数据就正常显示看板，不能把内容整个盖掉。
 * 顺序有意：先判"后端通不通"，再判"是不是读失败"，最后才是"真的空"。
 */
const boardState = computed<'' | 'down' | 'error' | 'loading' | 'empty'>(() => {
  if (rows.value.length) return ''
  if (ui.healthy === false) return 'down'
  if (failed.value) return 'error'
  if (loading.value) return 'loading'
  return 'empty'
})

const boardTitle = computed(() => {
  switch (boardState.value) {
    case 'down':
      return '后端没连上'
    case 'error':
      return '读取失败'
    case 'loading':
      return '正在读取审批记录…'
    default:
      return '还没有任何审批记录'
  }
})

const boardText = computed(() => {
  switch (boardState.value) {
    case 'down':
      return '审批记录存在后端（ticket-server 的 SQLite）里，前端只是读它。后端起来之后这一页就会有内容。'
    case 'error':
      return message.value || '请求没有成功，点重试再来一次。'
    case 'loading':
      return '正在从 /api/v1/approvals 拉数据。'
    default:
      return '员工在聊天里做可逆写会先出「确认单」，做不可逆写会进「审批」。这两类决定都会落到这里留痕。'
  }
})

/** 重试时先把健康状态重查一遍，否则后端刚起来页面还显示"没连上"。 */
async function retry() {
  await ui.refreshHealth()
  await load()
}

/**
 * 按风险反推"这一步在等谁"，和 backend 的 GATE_BY_RISK 对齐：
 * 不可逆写 → 等 approver；可逆写 → 等提单人本人。前端提前拦，省一次 403 请求。
 */
function blockedReason(row: ApprovalRow): string {
  if (row.status !== 'pending') return '这条已经处理过了'
  if (!row.thread_id) return '缺 thread_id —— 命令行直连产生的记录，网页端无法恢复那条会话'
  if (row.risk === 'write_irreversible') {
    if (!identity.isApprover) return '当前身份没有 approver 角色，无法批准不可逆写'
    if (row.requester === identity.userId) return '发起人不能批准自己的单，切成主管身份再来'
    return ''
  }
  if (row.requester !== identity.userId) return '这一步只等提单人本人确认，别人点会被后端拒绝'
  return ''
}

async function decide(row: ApprovalRow, type: 'approve' | 'reject', reason = '') {
  if (acting.value !== null) return
  const blocked = blockedReason(row)
  if (blocked && type === 'approve') {
    ElMessage.warning(blocked)
    return
  }
  if (!row.thread_id) {
    ElMessage.warning('这条记录没有 thread_id，无法恢复会话')
    return
  }
  acting.value = row.id
  message.value = ''
  try {
    await resumeStream(
      row.thread_id,
      { decision: { type, message: type === 'reject' ? reason || '审批人驳回：风险不可接受' : '' } },
      identity.headers,
      { onEvent: () => {} },
    )
    ElMessage.success(type === 'approve' ? '已通过，后端刚用同一条 thread 恢复了会话' : '已驳回，工单状态没动')
    active.value = null
    rejectReason.value = ''
    await load()
  } catch (err) {
    message.value = err instanceof Error ? err.message : String(err)
    await load()
  } finally {
    acting.value = null
  }
}

function open(row: ApprovalRow) {
  active.value = row
  rejectReason.value = ''
}

function close() {
  active.value = null
}

/** 别人还在别处审批时，这一页不该停在旧数据上：失焦回来 + 每 30 秒静默刷新一次。 */
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
  <div class="approvals">
    <div class="board-head">
      <div class="stats">
        <div class="stat">
          <div class="stat-k">待我处理</div>
          <div class="stat-v">{{ pending.length }}<span class="stat-u">条</span></div>
          <div class="stat-foot">{{ pending.filter((row) => row.risk === 'write_irreversible').length }} 条不可逆写</div>
        </div>
        <div class="stat">
          <div class="stat-k">今日已通过</div>
          <div class="stat-v">{{ todayPassed }}<span class="stat-u">条</span></div>
          <div class="stat-foot">通过即用 thread_id 恢复执行</div>
        </div>
        <div class="stat">
          <div class="stat-k">已驳回</div>
          <div class="stat-v">{{ rejected.length }}<span class="stat-u">条</span></div>
          <div class="stat-foot">驳回不产生任何写操作</div>
        </div>
        <div class="stat">
          <div class="stat-k">平均停留</div>
          <div class="stat-v">{{ avgStay }}</div>
          <div class="stat-foot">从发起决定，历史记录均值</div>
        </div>
      </div>

      <div class="head-right">
        <span class="upd">{{ updatedAt ? `最近更新 ${clock(updatedAt)}` : '还没读过数据' }}</span>
        <button type="button" class="btn ghost sm" :disabled="loading" @click="load()">
          <AppIcon name="refresh" :size="13" /> {{ loading ? '刷新中' : '刷新' }}
        </button>
      </div>
    </div>

    <p v-if="message && !boardState" class="banner">{{ message }}</p>

    <!-- 内容区正中间的大状态：一屏空白最容易被当成"页面坏了"或"项目是空的" -->
    <div v-if="boardState" class="state" :class="{ bad: boardState === 'down' || boardState === 'error' }">
      <div class="ico">
        <AppIcon :name="boardState === 'empty' ? 'shield' : 'alert'" :size="20" />
      </div>
      <h3>{{ boardTitle }}</h3>
      <p>{{ boardText }}</p>
      <div v-if="boardState === 'loading'" class="skel">
        <i style="width: 78%" /><i style="width: 56%" /><i style="width: 68%" />
      </div>
      <template v-else>
        <div class="acts">
          <button type="button" class="btn primary sm" @click="retry">
            <AppIcon name="refresh" :size="13" />
            {{ boardState === 'down' ? '重试连接' : boardState === 'error' ? '重试' : '刷新一下' }}
          </button>
        </div>
        <p v-if="boardState === 'down'" class="hint">
          启动后端：<code>python -m uvicorn backend.app.api.main:app --port 8010</code>
        </p>
      </template>
    </div>

    <div v-else class="columns">
      <section class="col">
        <header class="col-head">
          <span class="dot warn" />
          <span class="col-title">待我处理</span>
          <span class="col-count">{{ pending.length }}</span>
          <span class="col-hint">按风险排序</span>
        </header>
        <div class="col-body">
          <article v-for="row in pendingShown" :key="row.id" class="card" @click="open(row)">
            <div class="card-top">
              <span class="risk" :class="`risk-${riskMeta(row.risk).key}`">{{ riskMeta(row.risk).text }}</span>
              <span class="card-gate">{{ gateText(riskMeta(row.risk).gate) }}</span>
              <span class="card-time">{{ relTime(row.created_at) }}</span>
            </div>
            <h3 class="card-title">{{ row.summary || `${opLabel(row.op)} ${row.target}` }}</h3>
            <div class="card-meta">
              <span class="mono">{{ row.target || '—' }}</span>
            </div>
            <div class="card-people">
              <span>发起 {{ displayName(row.requester) }}</span>
              <span class="mono">会话 {{ row.thread_id || '缺失' }}</span>
            </div>
            <div class="card-actions" @click.stop>
              <button
                type="button"
                class="btn primary sm"
                :disabled="acting === row.id || Boolean(blockedReason(row))"
                :title="blockedReason(row)"
                @click="decide(row, 'approve')"
              >
                通过
              </button>
              <button type="button" class="btn danger sm" :disabled="acting === row.id" @click="decide(row, 'reject')">
                驳回
              </button>
              <span class="card-note">{{ blockedReason(row) || '点通过会用该会话的 thread_id 恢复执行' }}</span>
            </div>
          </article>

          <div v-if="pending.length > LIMIT" class="more">还有 {{ pending.length - LIMIT }} 条更早的待办，处理完上面这些会自动补位</div>

          <div v-if="!pending.length" class="empty">
            <div class="ico"><AppIcon name="check" :size="17" /></div>
            <p>这一刻没有待办</p>
            <p class="sub">员工发起不可逆写、或可逆写等本人确认时会出现在这里</p>
            <button type="button" class="btn ghost sm" @click="load()">
              <AppIcon name="refresh" :size="12" /> 刷新
            </button>
          </div>
        </div>
      </section>

      <section class="col">
        <header class="col-head">
          <span class="dot ok" />
          <span class="col-title">已通过</span>
          <span class="col-count">{{ passed.length }}</span>
          <span class="col-hint">今天</span>
        </header>
        <div class="col-body">
          <article v-for="row in passedShown" :key="row.id" class="card done" @click="open(row)">
            <div class="card-top">
              <span class="risk" :class="`risk-${riskMeta(row.risk).key}`">{{ riskMeta(row.risk).text }}</span>
              <span class="pill ok">{{ row.status === 'edited' ? '改后通过' : '已通过' }}</span>
              <span class="card-time">{{ clock(row.decided_at) }}</span>
            </div>
            <h3 class="card-title">{{ row.summary || `${opLabel(row.op)} ${row.target}` }}</h3>
            <div class="card-meta"><span class="mono">{{ row.target || '—' }}</span></div>
            <div class="card-people">
              <span>批准 {{ displayName(row.approver) }}</span>
              <span class="mono">{{ row.op }}</span>
            </div>
            <div class="tags">
              <span v-if="row.approver === row.requester" class="pill bad">自审</span>
              <span v-else class="pill ok">非自审</span>
              <span v-if="row.thread_id" class="pill ghost">thread 已回连</span>
            </div>
          </article>

          <div v-if="passed.length > LIMIT" class="more">还有 {{ passed.length - LIMIT }} 条更早的通过记录</div>

          <div v-if="!passed.length" class="empty">
            <div class="ico"><AppIcon name="clock" :size="17" /></div>
            <p>还没有通过的审批</p>
            <p class="sub">通过之后这里留痕：谁批的、批的什么、是不是自审</p>
          </div>
        </div>
      </section>

      <section class="col">
        <header class="col-head">
          <span class="dot bad" />
          <span class="col-title">已驳回</span>
          <span class="col-count">{{ rejected.length }}</span>
          <span class="col-hint">最近 7 天</span>
        </header>
        <div class="col-body">
          <article v-for="row in rejectedShown" :key="row.id" class="card done" @click="open(row)">
            <div class="card-top">
              <span class="risk" :class="`risk-${riskMeta(row.risk).key}`">{{ riskMeta(row.risk).text }}</span>
              <span class="pill bad">已驳回</span>
              <span class="card-time">{{ relTime(row.decided_at) }}</span>
            </div>
            <h3 class="card-title">{{ row.summary || `${opLabel(row.op)} ${row.target}` }}</h3>
            <div class="card-meta"><span class="mono">{{ row.target || '—' }}</span></div>
            <div class="card-people">
              <span>驳回 {{ displayName(row.approver) }}</span>
            </div>
            <p class="card-reason">{{ row.note || '没有填驳回理由' }}</p>
            <div class="tags"><span class="pill ghost">动作未执行</span></div>
          </article>

          <div v-if="rejected.length > LIMIT" class="more">还有 {{ rejected.length - LIMIT }} 条更早的驳回记录</div>

          <div v-if="!rejected.length" class="empty">
            <div class="ico"><AppIcon name="shield" :size="17" /></div>
            <p>没有驳回记录</p>
            <p class="sub">驳回不产生任何写操作，工单状态保持原样</p>
          </div>
        </div>
      </section>
    </div>

    <!-- 抽屉：决策细节都放这儿，列表不被撑爆 -->
    <div v-if="active" class="scrim" @click="close" />
    <aside v-if="active" class="drawer">
      <header class="dr-head">
        <div>
          <div class="dr-kicker">审批单 #{{ active.id }}</div>
          <div class="dr-thread mono">{{ active.thread_id || '缺 thread_id' }}</div>
        </div>
        <span class="risk" :class="`risk-${riskMeta(active.risk).key}`">{{ riskMeta(active.risk).text }}</span>
        <button type="button" class="icon-btn" @click="close"><AppIcon name="close" :size="15" /></button>
      </header>

      <div class="dr-body">
        <section class="dr-sec">
          <div class="sec-label">动作</div>
          <div class="dr-title">{{ active.summary || `${opLabel(active.op)} ${active.target}` }}</div>
          <div class="dr-sub mono">{{ active.op }} · {{ active.target || '—' }}</div>
        </section>

        <section class="dr-sec">
          <div class="sec-label">为什么需要{{ active.risk === 'write_irreversible' ? '审批' : '确认' }}</div>
          <div class="dr-note">
            {{
              active.risk === 'write_irreversible'
                ? '这一步属于不可逆写：外发通知或发布内容之后无法撤回，所以按 action_spec.compute_risk 的规则升级到审批门，需要 approver 角色批准。'
                : '这一步会改数据但可以回滚，所以只要求提单人本人确认，不惊动主管。'
            }}
          </div>
        </section>

        <section class="dr-sec">
          <div class="sec-label">基本信息</div>
          <div class="kv">
            <div class="kv-row"><span>发起人</span><b>{{ displayName(active.requester) }}</b></div>
            <div class="kv-row"><span>发起时间</span><b>{{ active.created_at || '—' }}</b></div>
            <div class="kv-row"><span>闸门</span><b>{{ gateText(riskMeta(active.risk).gate) }}</b></div>
            <div class="kv-row"><span>状态</span><b>{{ active.status }}</b></div>
            <div v-if="active.approver" class="kv-row"><span>处理人</span><b>{{ displayName(active.approver) }}</b></div>
            <div v-if="active.decided_at" class="kv-row"><span>处理时间</span><b>{{ active.decided_at }}</b></div>
          </div>
        </section>

        <section v-if="active.note" class="dr-sec">
          <div class="sec-label">备注</div>
          <div class="dr-note">{{ active.note }}</div>
        </section>

        <section v-if="active.status === 'pending'" class="dr-sec">
          <div class="sec-label">驳回理由（可选）</div>
          <input v-model="rejectReason" class="dr-input" placeholder="填了会写进 approvals.note" />
        </section>
      </div>

      <footer v-if="active.status === 'pending'" class="dr-foot">
        <button
          type="button"
          class="btn primary"
          :disabled="acting === active.id || Boolean(blockedReason(active))"
          :title="blockedReason(active)"
          @click="decide(active, 'approve', rejectReason)"
        >
          通过并执行
        </button>
        <button type="button" class="btn danger" :disabled="acting === active.id" @click="decide(active, 'reject', rejectReason)">
          驳回
        </button>
        <span class="dr-hint">{{ blockedReason(active) || '通过会用这条 thread 恢复执行，结果回到聊天里' }}</span>
      </footer>
    </aside>
  </div>
</template>

<style scoped>
.approvals {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 18px 26px 26px;
}

.board-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}
.head-right {
  display: flex;
  align-items: center;
  gap: 9px;
  flex: none;
  padding-top: 2px;
}
.upd {
  font-size: 10.6px;
  color: var(--ink-4);
  white-space: nowrap;
}
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.stat {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: var(--r);
  padding: 11px 13px 10px;
  box-shadow: var(--sh-1);
}
.stat-k {
  font-size: 10.4px;
  color: var(--ink-4);
  font-weight: 620;
}
.stat-v {
  font-size: 21px;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.3;
  margin-top: 2px;
}
.stat-u {
  font-size: 11px;
  font-weight: 500;
  color: var(--ink-4);
  margin-left: 3px;
}
.stat-foot {
  font-size: 10px;
  color: var(--ink-4);
  margin-top: 2px;
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

.columns {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-top: 14px;
  align-items: start;
}
.col {
  background: var(--paper-2);
  border: 1px solid var(--line);
  border-radius: var(--r-lg);
  padding: 11px;
}
.col-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 3px 9px;
}
.col-head .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.dot.warn {
  background: #d98613;
}
.dot.ok {
  background: #18a05a;
}
.dot.bad {
  background: var(--bad);
}
.col-title {
  font-size: 11.8px;
  font-weight: 680;
}
.col-count {
  font-size: 10.4px;
  color: var(--ink-4);
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0 6px;
}
.col-hint {
  margin-left: auto;
  font-size: 10px;
  color: var(--ink-4);
}
.col-body {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.card {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: var(--r);
  padding: 10px 11px 11px;
  box-shadow: var(--sh-1);
  cursor: pointer;
  transition: box-shadow 0.14s, transform 0.14s, border-color 0.14s;
}
.card:hover {
  box-shadow: var(--sh-2);
  border-color: var(--line-2);
  transform: translateY(-1px);
}
.card.done {
  box-shadow: none;
}
.card-top {
  display: flex;
  align-items: center;
  gap: 6px;
}
.card-gate {
  font-size: 10px;
  color: var(--ink-4);
}
.card-time {
  margin-left: auto;
  font-size: 10px;
  color: var(--ink-4);
}
.card-title {
  margin: 7px 0 0;
  font-size: 12.6px;
  font-weight: 640;
  line-height: 1.5;
}
.card-meta {
  margin-top: 3px;
  font-size: 10.4px;
  color: var(--ink-4);
}
.card-people {
  display: flex;
  flex-direction: column;
  gap: 1px;
  margin-top: 7px;
  font-size: 10.4px;
  color: var(--ink-3);
}
.card-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding-top: 9px;
  border-top: 1px solid var(--line);
}
.card-note {
  font-size: 9.7px;
  line-height: 1.4;
  color: var(--ink-4);
  min-width: 0;
}
.more {
  padding: 10px 4px 2px;
  font-size: 10.5px;
  color: var(--ink-4);
  text-align: center;
}
.card-reason {
  margin: 7px 0 0;
  font-size: 10.8px;
  line-height: 1.55;
  color: var(--ink-3);
  padding: 6px 8px;
  border-radius: 6px;
  background: var(--paper-2);
  border: 1px dashed var(--line-2);
}
.tags {
  display: flex;
  gap: 5px;
  margin-top: 8px;
}

.scrim {
  position: fixed;
  inset: 0;
  background: rgba(16, 19, 25, 0.28);
  backdrop-filter: blur(1.5px);
  z-index: 40;
  animation: fade 0.2s ease;
}
.drawer {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: 440px;
  background: var(--paper);
  border-left: 1px solid var(--line-2);
  box-shadow: -18px 0 48px rgba(16, 19, 25, 0.14);
  z-index: 41;
  display: flex;
  flex-direction: column;
  animation: slide 0.24s ease;
}
.dr-head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 14px 16px 12px;
  border-bottom: 1px solid var(--line);
}
.dr-kicker {
  font-size: 11.4px;
  font-weight: 680;
}
.dr-thread {
  font-size: 10.2px;
  color: var(--ink-4);
  margin-top: 2px;
}
.dr-head .risk {
  margin-left: auto;
}
.icon-btn {
  border: 0;
  background: transparent;
  color: var(--ink-4);
  cursor: pointer;
  padding: 2px;
  border-radius: 6px;
}
.icon-btn:hover {
  background: var(--paper-2);
  color: var(--ink-2);
}
.dr-body {
  flex: 1;
  overflow-y: auto;
  padding: 4px 16px 16px;
}
.dr-sec {
  padding: 12px 0;
  border-bottom: 1px solid var(--line);
}
.dr-sec:last-child {
  border-bottom: 0;
}
.dr-title {
  margin-top: 6px;
  font-size: 13.4px;
  font-weight: 650;
  line-height: 1.5;
}
.dr-sub {
  margin-top: 3px;
  font-size: 10.6px;
  color: var(--ink-4);
}
.dr-note {
  margin-top: 6px;
  font-size: 11.6px;
  line-height: 1.7;
  color: var(--ink-2);
  padding: 8px 10px;
  border-radius: var(--r-sm);
  background: var(--warn-tint);
  border: 1px solid var(--warn-line);
}
.kv {
  margin-top: 5px;
}
.kv-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 5px 0;
  font-size: 11.2px;
  border-bottom: 1px dashed var(--line);
}
.kv-row:last-child {
  border-bottom: 0;
}
.kv-row span {
  color: var(--ink-4);
}
.kv-row b {
  font-weight: 600;
  color: var(--ink-2);
}
.dr-input {
  width: 100%;
  margin-top: 6px;
  border: 1px solid var(--line-2);
  border-radius: var(--r-sm);
  padding: 7px 9px;
  font: inherit;
  font-size: 12px;
  outline: 0;
}
.dr-input:focus {
  border-color: #a9b7f2;
  box-shadow: 0 0 0 3px rgba(58, 86, 212, 0.09);
}
.dr-foot {
  flex: none;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 16px;
  border-top: 1px solid var(--line);
  background: var(--paper-2);
}
.dr-hint {
  font-size: 9.9px;
  line-height: 1.4;
  color: var(--ink-4);
  margin-left: auto;
  text-align: right;
  max-width: 150px;
}
</style>
