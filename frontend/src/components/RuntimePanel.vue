<script setup lang="ts">
/**
 * 右侧「运行时」面板。
 *
 * 面试演示时这块是讲故事的地方：现在跑到哪个节点、为什么停、风险在第几级、
 * 落库/落库前的结构化结果是什么、等价命令行怎么复现。所以它默认展开，
 * 但允许收起（演示以外的时间它确实占地方）。
 */

import { computed, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import { gateText, riskMeta } from '@/utils/format'
import type { RunDetail, TraceItem } from '@/types'

const props = defineProps<{
  detail: RunDetail | null
  nodes: TraceItem[]
  running: boolean
  elapsedMs: number | null
  tokens: { in: number; out: number } | null
}>()

interface NodeSpec {
  key: string
  label: string
  icon: string
}

const NODES: NodeSpec[] = [
  { key: 'classify_request', label: '理解意图', icon: 'search' },
  { key: 'gather_evidence', label: '取证据', icon: 'book' },
  { key: 'answer_with_citations', label: '作答', icon: 'chat' },
  { key: 'plan_action', label: '制定动作', icon: 'code' },
  { key: 'ask_missing_info', label: '澄清门', icon: 'alert' },
  { key: 'confirm_action', label: '确认闸门', icon: 'check' },
  { key: 'approve_action', label: '审批闸门', icon: 'shield' },
  { key: 'execute_action', label: '执行写操作', icon: 'send' },
  { key: 'compose_reply', label: '组织回复', icon: 'chat' },
]

const copied = ref('')

const traceMap = computed(() => {
  const map = new Map<string, TraceItem>()
  for (const item of props.nodes) map.set(item.node, item)
  return map
})

const current = computed(() => props.detail?.next?.[0] ?? '')

/** 从 checkpoint 恢复的会话没有逐节点 trace，按"停在哪一格"回推前面的格子。 */
const derivedFrom = computed(() => {
  if (props.nodes.length || !props.detail?.paused) return -1
  return NODES.findIndex((spec) => spec.key === current.value)
})

function skipByName(key: string): boolean {
  const d = props.detail
  if (!d) return false
  if (key === 'answer_with_citations') return d.intent !== 'knowledge'
  if (key === 'ask_missing_info') return true
  if (key === 'confirm_action') return d.risk === 'write_irreversible'
  if (key === 'approve_action') return d.risk !== 'write_irreversible'
  return false
}

const rows = computed(() =>
  NODES.map((spec, index) => {
    const hit = traceMap.value.get(spec.key)
    let state: 'done' | 'now' | 'skip' | 'pending' = 'pending'
    if (hit) state = 'done'
    else if (props.running && spec.key === current.value) state = 'now'
    else if (!props.running && props.detail && !props.detail.paused) state = 'skip'
    else if (spec.key === current.value) state = 'now'
    else if (derivedFrom.value > index) state = skipByName(spec.key) ? 'skip' : 'done'
    return {
      ...spec,
      state,
      info: hit?.info ?? (state === 'now' ? '进行中' : state === 'skip' ? '本轮跳过' : state === 'done' ? '已完成' : '未开始'),
      ms: hit?.ms,
    }
  }),
)

const doneCount = computed(() => rows.value.filter((row) => row.state === 'done').length)

const risk = computed(() => riskMeta(props.detail?.risk))

const headline = computed(() => {
  if (!props.detail) return '等待提问'
  if (props.running) return '执行中'
  if (props.detail.paused) return props.detail.risk === 'write_irreversible' ? '停在审批' : '停在确认'
  return '已完成'
})
const headTone = computed(() => {
  if (props.running) return 'accent'
  if (props.detail?.paused) return 'warn'
  if (props.detail) return 'ok'
  return 'ghost'
})

const server = computed(() => {
  const op = String(props.detail?.view?.op ?? '')
  return op === 'search_kb' || op === 'publish_kb_article' ? 'kb · stdio' : 'ticket · stdio'
})

const kv = computed(() => {
  const d = props.detail
  if (!d) return []
  // 还没执行时 ticket_no 还没写回 State，就从闸门卡片的参数里借一个显示
  const fieldNo = (d.interrupt?.fields ?? []).find((f) => f.name === 'ticket_no')?.value
  return [
    { k: '意图', v: d.intent || '-', mono: false },
    { k: '动作', v: d.view?.op || '-', mono: true },
    { k: '服务', v: server.value, mono: true },
    { k: '单号', v: d.ticket_no || (fieldNo ? String(fieldNo) : '-'), mono: true },
    { k: '下一站', v: d.next?.[0] || '—', mono: true },
    { k: '结果', v: d.outcome || '—', mono: true },
  ]
})

const elapsedText = computed(() => {
  if (props.elapsedMs === null) return ''
  return `${(props.elapsedMs / 1000).toFixed(1)}s`
})

const cliLines = computed(() => {
  const thread = props.detail?.thread_id || 'web-...'
  const lines = [`python -m scripts.run_graph state --thread ${thread}`]
  if (props.detail?.paused) {
    lines.push(`python -m scripts.run_graph resume --thread ${thread} --approve`)
  }
  return lines
})

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    copied.value = text
    setTimeout(() => {
      copied.value = ''
    }, 1400)
  } catch {
    /* 剪贴板不可用就算了，命令行本来也能手选 */
  }
}
</script>

<template>
  <aside class="runtime">
    <header class="rt-head">
      <span class="rt-title">运行时</span>
      <span class="pill" :class="headTone">{{ headline }}</span>
      <span v-if="elapsedText" class="rt-time mono">{{ elapsedText }}</span>
    </header>

    <div class="rt-scroll">
      <section class="rt-sec">
        <div class="rt-sec-head">
          <span class="sec-label">节点流水</span>
          <span class="rt-count mono">{{ doneCount }} / 9</span>
        </div>
        <ol class="nodes">
          <li v-for="row in rows" :key="row.key" class="node" :class="row.state">
            <span class="n-mark">
              <AppIcon v-if="row.state === 'done'" name="check" :size="11" />
              <span v-else-if="row.state === 'now'" class="n-pulse" />
              <span v-else class="n-dash" />
            </span>
            <div class="n-body">
              <div class="n-label">{{ row.label }}</div>
              <div class="n-info">
                <span class="mono">{{ row.key }}</span>
                <span v-if="row.ms !== undefined" class="n-ms">· {{ (row.ms / 1000).toFixed(1) }}s</span>
                <span class="n-desc">· {{ row.info }}</span>
              </div>
            </div>
          </li>
        </ol>
      </section>

      <section class="rt-sec">
        <div class="sec-label">风险等级</div>
        <div class="ladder">
          <span class="rung" :class="{ on: risk.key === 'read' }">只读</span>
          <span class="rung" :class="{ on: risk.key === 'rev' }">可逆写</span>
          <span class="rung" :class="{ on: risk.key === 'irr' }">不可逆写</span>
        </div>
        <div v-if="detail?.risk" class="risk-card">
          <div class="rc-top">
            <span class="mono rc-risk">{{ detail.risk }}</span>
            <span class="rc-gate">{{ gateText(detail.gate) }}</span>
          </div>
          <div class="rc-row">
            <span>{{ risk.gate === 'approve' ? '需要角色' : '需要动作' }}</span>
            <span class="mono">{{ risk.gate === 'approve' ? 'approver' : '本人确认' }}</span>
          </div>
          <div class="rc-row">
            <span>{{ risk.gate === 'approve' ? '发起人 ≠ 批准人' : '本人确认，不可代签' }}</span>
            <span class="rc-on">{{ risk.gate ? '已强制' : '不过闸门' }}</span>
          </div>
        </div>
      </section>

      <section v-if="detail" class="rt-sec">
        <div class="sec-label">本轮结构化结果</div>
        <div class="kv">
          <div v-for="item in kv" :key="item.k" class="kv-row">
            <span class="kv-k">{{ item.k }}</span>
            <span class="kv-v" :class="{ mono: item.mono }">{{ item.v }}</span>
          </div>
          <div v-if="tokens" class="kv-row">
            <span class="kv-k">token</span>
            <span class="kv-v mono">入 {{ tokens.in }} · 出 {{ tokens.out }}</span>
          </div>
        </div>
      </section>

      <section class="rt-sec">
        <div class="rt-sec-head">
          <span class="sec-label">等价命令行</span>
          <span class="rt-hint">可复现</span>
        </div>
        <div class="cli">
          <div v-for="line in cliLines" :key="line" class="cli-line">
            <code class="mono">{{ line }}</code>
            <button type="button" class="cli-copy" :title="copied === line ? '已复制' : '复制'" @click="copy(line)">
              <AppIcon :name="copied === line ? 'check' : 'code'" :size="12" />
            </button>
          </div>
        </div>
        <p class="rt-note">同一条 thread 的命令行等价操作：闸门是靠 checkpoint + 同一条 thread 恢复的。</p>
      </section>
    </div>
  </aside>
</template>

<style scoped>
.runtime {
  width: 348px;
  flex: none;
  border-left: 1px solid var(--line);
  background: var(--paper);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.rt-head {
  height: 44px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 14px;
  border-bottom: 1px solid var(--line);
}
.rt-title {
  font-size: 11.8px;
  font-weight: 680;
  letter-spacing: 0.02em;
  color: var(--ink-2);
}
.rt-time {
  margin-left: auto;
  font-size: 10.8px;
  color: var(--ink-4);
}
.rt-scroll {
  overflow-y: auto;
  min-height: 0;
  flex: 1;
  padding: 4px 14px 16px;
}
.rt-sec {
  padding: 11px 0;
  border-bottom: 1px solid var(--line);
}
.rt-sec:last-child {
  border-bottom: 0;
}
.rt-sec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.rt-count,
.rt-hint {
  font-size: 10px;
  color: var(--ink-4);
}

.nodes {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
}
.node {
  display: flex;
  gap: 8px;
  padding: 4px 0;
}
.n-mark {
  width: 13px;
  height: 13px;
  flex: none;
  margin-top: 2px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--ok-tint);
  color: var(--ok);
}
.node.pending .n-mark,
.node.skip .n-mark {
  background: var(--paper-2);
  border: 1px solid var(--line-2);
}
.node.now .n-mark {
  background: var(--warn-tint);
  border: 1px solid var(--warn-line);
}
.n-pulse {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--warn);
  animation: pulse 1.6s ease-in-out infinite;
}
.n-dash {
  width: 5px;
  height: 1px;
  background: var(--ink-4);
}
.n-body {
  min-width: 0;
}
.n-label {
  font-size: 11.8px;
  font-weight: 600;
  line-height: 1.35;
  color: var(--ink-2);
}
.node.pending .n-label,
.node.skip .n-label {
  color: var(--ink-4);
  font-weight: 500;
}
.node.now .n-label {
  color: var(--warn);
}
.n-info {
  font-size: 10.1px;
  line-height: 1.45;
  color: var(--ink-4);
  word-break: break-word;
}
.node.now .n-info {
  color: #a9600a;
}
.n-ms {
  color: var(--ink-4);
}

.ladder {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0;
  margin-top: 8px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  overflow: hidden;
}
.rung {
  text-align: center;
  font-size: 10.8px;
  padding: 5px 0;
  color: var(--ink-4);
  background: var(--paper-2);
}
.rung + .rung {
  border-left: 1px solid var(--line);
}
.rung.on {
  color: var(--ink);
  font-weight: 660;
  background: var(--brand-tint);
}
.rung.on:nth-child(2) {
  background: var(--warn-tint);
  color: #8a5209;
}
.rung.on:nth-child(3) {
  background: var(--bad-tint);
  color: #98261a;
}

.risk-card {
  margin-top: 9px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  padding: 8px 9px;
  background: var(--paper-2);
}
.rc-top {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.rc-risk {
  font-size: 11px;
  font-weight: 650;
  color: var(--ink);
  word-break: break-all;
}
.rc-gate {
  margin-left: auto;
  font-size: 10.4px;
  color: var(--ink-3);
}
.rc-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 5px;
  font-size: 10.6px;
  color: var(--ink-3);
}
.rc-on {
  color: var(--ok);
  font-weight: 620;
}

.kv {
  margin-top: 8px;
}
.kv-row {
  display: flex;
  gap: 10px;
  padding: 4.5px 0;
  border-bottom: 1px dashed var(--line);
}
.kv-row:last-child {
  border-bottom: 0;
}
.kv-k {
  width: 52px;
  flex: none;
  font-size: 10.8px;
  color: var(--ink-4);
}
.kv-v {
  font-size: 11.3px;
  color: var(--ink-2);
  min-width: 0;
  word-break: break-all;
}

.cli {
  margin-top: 8px;
  border-radius: var(--r-sm);
  background: #1b2030;
  padding: 8px 9px;
}
.cli-line {
  display: flex;
  align-items: flex-start;
  gap: 6px;
}
.cli-line + .cli-line {
  margin-top: 3px;
}
.cli-line code {
  flex: 1;
  min-width: 0;
  font-size: 10.2px;
  line-height: 1.55;
  color: #c8d2f0;
  word-break: break-all;
}
.cli-copy {
  flex: none;
  border: 0;
  background: transparent;
  color: #6f7c9e;
  cursor: pointer;
  padding: 1px;
}
.cli-copy:hover {
  color: #c8d2f0;
}
.rt-note {
  margin: 7px 0 0;
  font-size: 10.2px;
  line-height: 1.55;
  color: var(--ink-4);
}
</style>
