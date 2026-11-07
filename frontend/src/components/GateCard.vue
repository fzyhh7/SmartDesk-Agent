<script setup lang="ts">
/**
 * 闸门卡片 —— 全项目最重要的一个组件。
 *
 * 它不是"提示条"，而是一张**可审阅的单据**：为什么被拦下来、要执行什么、
 * 每个参数是谁给的（证据回填 / 用户原话）、还差谁的批准。审批人在这里做的决定
 * 会直接决定后端是否执行那次写操作，所以信息必须一次给全，不能藏在折叠区里。
 */

import { computed, ref, watch } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import { displayName } from '@/utils/people'
import { riskMeta } from '@/utils/format'
import type { ActionField, Citation, InterruptPayload } from '@/types'

const props = defineProps<{ payload: InterruptPayload; disabled?: boolean }>()
const emit = defineEmits<{ submit: [body: Record<string, unknown>]; approvals: [] }>()

/** 澄清门缺的字段名是后端给的英文键，这里翻成人话；没有映射就原样显示。 */
const MISSING_LABEL: Record<string, string> = {
  ticket_no: '工单号',
  title: '标题',
  content: '正文内容',
  description: '问题描述',
  resolution: '处理结论',
  urgency: '优先级',
  category: '分类',
  contact: '联系方式',
  notify_reporter: '是否通知提单人',
}

const kindIcon = computed(() => {
  if (props.payload.type === 'clarify') return 'alert'
  if (props.payload.type === 'approve') return 'shield'
  return 'check'
})

const kicker = computed(() => {
  if (props.payload.type === 'clarify') return '补充信息 · CLARIFY'
  if (props.payload.type === 'approve') return '审批单 · APPROVE'
  return '确认单 · CONFIRM'
})

const risk = computed(() => riskMeta(props.payload.risk))

const fields = computed<ActionField[]>(() => props.payload.fields ?? [])
const citations = computed<Citation[]>(() => props.payload.citations ?? [])
const options = computed<string[]>(() => props.payload.options ?? [])
const missing = computed<string[]>(() => props.payload.missing ?? [])

const headline = computed(
  () => props.payload.title || props.payload.summary || (props.payload.type === 'clarify' ? '还需要一点信息' : '请确认这次操作'),
)

/** 当前身份就是发起人、且不具备审批资格时，后端给的是 mode='request'。 */
const isRequest = computed(() => props.payload.mode === 'request')
const requester = computed(() => props.payload.requested_by || '')
const requiredRoles = computed(() => (props.payload.required_roles ?? []).join(' / ') || '有权限的人')

const editable = ref<Record<string, string>>({})
const answers = ref<Record<string, string>>({})
const rejectMessage = ref('')

function toStringValue(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

watch(
  () => props.payload,
  (payload) => {
    const next: Record<string, string> = {}
    for (const field of payload.fields ?? []) next[field.name] = toStringValue(field.value)
    editable.value = next

    const draft: Record<string, string> = {}
    for (const name of payload.missing ?? []) draft[name] = ''
    answers.value = draft
    rejectMessage.value = ''
  },
  { immediate: true, deep: true },
)

/** 只把改过的字段放进 patch —— 一个都没改就是单纯的 approve，不制造假改动。 */
const patch = computed<Record<string, unknown>>(() => {
  const result: Record<string, unknown> = {}
  for (const field of fields.value) {
    const now = editable.value[field.name] ?? ''
    if (now === toStringValue(field.value)) continue
    try {
      result[field.name] = JSON.parse(now)
    } catch {
      result[field.name] = now
    }
  }
  return result
})

const changed = computed(() => Object.keys(patch.value).length > 0)

function pickOption(option: string) {
  const first = Object.keys(answers.value)[0] ?? 'ticket_no'
  answers.value = { ...answers.value, [first]: option }
}

function submitAnswers() {
  emit('submit', { answers: { ...answers.value } })
}

function approve() {
  emit('submit', { decision: changed.value ? { type: 'edit', patch: patch.value } : { type: 'approve' } })
}

function reject() {
  emit('submit', { decision: { type: 'reject', message: rejectMessage.value } })
}
</script>

<template>
  <article class="doc" :class="`doc-${risk.key}`">
    <header class="doc-head">
      <span class="doc-icon"><AppIcon :name="kindIcon" :size="15" /></span>
      <div class="doc-headmain">
        <div class="doc-kicker">{{ kicker }}</div>
        <h3 class="doc-title">{{ headline }}</h3>
      </div>
      <div class="doc-meta">
        <span v-if="payload.risk" class="risk" :class="`risk-${risk.key}`">{{ risk.text }}</span>
        <span v-if="payload.mode === 'request'" class="doc-mode">等审批</span>
        <span v-else-if="payload.type === 'confirm'" class="doc-mode">等你确认</span>
      </div>
    </header>

    <!-- 为什么被拦下来：这段是给人做决定用的，不是日志 -->
    <div v-if="payload.hint" class="doc-reason">
      <span class="ri">!</span>
      <p>{{ payload.hint }}</p>
    </div>

    <!-- 澄清门：只问缺的那几个值 -->
    <div v-if="payload.type === 'clarify'" class="doc-body">
      <div class="ask">
        <label v-for="name in missing" :key="name" class="ask-row">
          <span class="ask-label">{{ MISSING_LABEL[name] ?? name }}</span>
          <input v-model="answers[name]" class="fld" placeholder="补上这个值" :disabled="disabled" />
        </label>
      </div>
      <div v-if="options.length" class="options">
        <span class="options-label">候选</span>
        <button v-for="option in options" :key="option" type="button" class="chip" :disabled="disabled" @click="pickOption(option)">
          {{ option }}
        </button>
      </div>
      <div class="doc-foot">
        <span class="doc-status"><AppIcon name="alert" :size="13" /> 缺参数时先问，不会拿猜的值去执行</span>
        <button type="button" class="btn primary sm" :disabled="disabled" @click="submitAnswers">补充并继续</button>
      </div>
    </div>

    <!-- 确认单 / 审批单：参数可改，然后通过或驳回 -->
    <div v-else class="doc-body">
      <div class="doc-grid">
        <div class="doc-fields">
          <div class="sec-label">动作参数</div>
          <table class="fields">
            <tbody>
              <tr v-for="field in fields" :key="field.name">
                <td class="f-label">{{ field.label }}</td>
                <td class="f-value">
                  <input
                    v-model="editable[field.name]"
                    class="fld"
                    :disabled="disabled || field.editable === false"
                    :title="field.editable === false ? '这个字段由服务端决定，不可改' : ''"
                  />
                </td>
                <td class="f-src">
                  <span v-if="field.source === 'from_evidence'" class="src-chip ev">证据回填</span>
                  <span v-else-if="field.source === 'from_user'" class="src-chip me">你说的话</span>
                  <span v-else-if="field.source === 'from_context'" class="src-chip">上下文</span>
                  <span v-else-if="field.editable === false" class="src-chip ro">只读</span>
                  <span v-else class="src-chip">默认值</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="changed" class="changed-tip">
            改过 {{ Object.keys(patch).join('、') }} —— 后端会按新参数重算风险，可能再升一级
          </div>
        </div>

        <aside class="doc-side">
          <div class="sec-label">审批链</div>
          <ol class="chain">
            <li>
              <span class="dn dot" />
              <div>
                <div class="dn-name">{{ displayName(requester) }}</div>
                <div class="dn-sub">发起人 · 此人不能批准自己的单</div>
              </div>
            </li>
            <li>
              <span class="dn ring" />
              <div>
                <div class="dn-name">{{ isRequest ? requiredRoles : '等你处理' }}</div>
                <div class="dn-sub">{{ risk.gate === 'approve' ? 'approver 角色二次鉴权' : '提单人本人确认' }}</div>
              </div>
            </li>
            <li>
              <span class="dn hollow" />
              <div>
                <div class="dn-name">execute_action</div>
                <div class="dn-sub">唯一写节点 · 走 MCP 服务端</div>
              </div>
            </li>
          </ol>

          <div v-if="citations.length" class="ev-box">
            <div class="ev-title">依据</div>
            <div v-for="citation in citations" :key="citation" class="ev-line">{{ citation }}</div>
          </div>
        </aside>
      </div>

      <label v-if="payload.type === 'approve' && !isRequest" class="reject-row">
        <span class="ask-label">驳回理由（可选）</span>
        <input v-model="rejectMessage" class="fld" placeholder="填了会写进 approvals.note" :disabled="disabled" />
      </label>

      <footer class="doc-foot">
        <span class="doc-status">
          <AppIcon name="clock" :size="13" />
          <template v-if="isRequest">已提交审批 · 等 {{ requiredRoles }}</template>
          <template v-else-if="payload.type === 'confirm'">等你本人确认，别人替你点会被拒</template>
          <template v-else>等你决定，通过后立刻执行</template>
        </span>
        <span class="doc-note" v-if="isRequest">发起人不能批准自己的单，切到主管身份可在「审批中心」直接处理</span>
        <button v-if="isRequest" type="button" class="btn sm ghost" @click="emit('approvals')">
          去审批中心
        </button>
        <template v-else>
          <button type="button" class="btn danger sm" :disabled="disabled" @click="reject">驳回</button>
          <button type="button" class="btn primary sm" :disabled="disabled" @click="approve">
            {{ changed ? '改完并通过' : payload.type === 'confirm' ? '确认执行' : '通过并执行' }}
          </button>
        </template>
      </footer>
    </div>
  </article>
</template>

<style scoped>
.doc {
  background: var(--paper);
  border: 1px solid var(--line-2);
  border-left: 3px solid var(--warn);
  border-radius: var(--r);
  box-shadow: var(--sh-2);
  overflow: hidden;
}
.doc-read {
  border-left-color: var(--line-2);
}
.doc-rev {
  border-left-color: var(--warn);
}
.doc-irr {
  border-left-color: var(--bad);
}

.doc-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 13px 15px 11px;
  border-bottom: 1px solid var(--line);
}
.doc-icon {
  width: 26px;
  height: 26px;
  flex: none;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: var(--warn-tint);
  color: var(--warn);
}
.doc-irr .doc-icon {
  background: var(--bad-tint);
  color: var(--bad);
}
.doc-headmain {
  flex: 1;
  min-width: 0;
}
.doc-kicker {
  font-size: 10.2px;
  font-weight: 700;
  letter-spacing: 0.09em;
  color: var(--ink-4);
}
.doc-title {
  margin: 3px 0 0;
  font-size: 14.2px;
  font-weight: 660;
  line-height: 1.4;
  letter-spacing: -0.01em;
}
.doc-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: none;
}
.doc-mode {
  font-size: 11px;
  color: var(--ink-3);
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--paper-2);
  border: 1px solid var(--line);
}

.doc-reason {
  display: flex;
  gap: 9px;
  margin: 12px 15px 0;
  padding: 9px 11px;
  border-radius: var(--r-sm);
  background: var(--warn-tint);
  border: 1px solid var(--warn-line);
}
.doc-irr .doc-reason {
  background: var(--bad-tint);
  border-color: var(--bad-line);
}
.doc-reason .ri {
  width: 15px;
  height: 15px;
  flex: none;
  margin-top: 1px;
  border-radius: 50%;
  background: var(--warn);
  color: #fff;
  font-size: 10.5px;
  font-weight: 700;
  display: grid;
  place-items: center;
}
.doc-irr .doc-reason .ri {
  background: var(--bad);
}
.doc-reason p {
  margin: 0;
  font-size: 11.9px;
  line-height: 1.6;
  color: #7c4a08;
}
.doc-irr .doc-reason p {
  color: #8d2216;
}

.doc-body {
  padding: 12px 15px 0;
}

.doc-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 186px;
  gap: 16px;
}

.fields {
  width: 100%;
  border-collapse: collapse;
}
.fields td {
  padding: 6px 0;
  border-bottom: 1px solid var(--line);
  vertical-align: middle;
}
.fields tr:last-child td {
  border-bottom: 0;
}
.f-label {
  width: 74px;
  color: var(--ink-3);
  font-size: 11.7px;
  white-space: nowrap;
  padding-right: 8px !important;
}
.f-src {
  width: 82px;
  text-align: right;
}

.fld {
  width: 100%;
  min-width: 0;
  border: 1px solid transparent;
  background: transparent;
  border-radius: 6px;
  padding: 3px 6px;
  font: inherit;
  font-size: 12.3px;
  color: var(--ink);
  transition: border-color 0.13s, background 0.13s;
}
.fld:hover:not(:disabled) {
  border-color: var(--line-2);
  background: var(--paper-2);
}
.fld:focus {
  outline: 0;
  border-color: #a9b7f2;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(58, 86, 212, 0.09);
}
.fld:disabled {
  color: var(--ink-3);
  cursor: default;
}

.changed-tip {
  margin-top: 7px;
  font-size: 11.2px;
  color: var(--warn);
}

.doc-side {
  border-left: 1px solid var(--line);
  padding-left: 14px;
}

.chain {
  list-style: none;
  margin: 0;
  padding: 0;
}
.chain li {
  position: relative;
  display: flex;
  gap: 8px;
  padding-bottom: 11px;
}
.chain li:last-child {
  padding-bottom: 0;
}
.chain li:not(:last-child)::after {
  content: '';
  position: absolute;
  left: 5px;
  top: 13px;
  bottom: 1px;
  width: 1px;
  background: var(--line-2);
}
.chain .dn {
  width: 11px;
  height: 11px;
  flex: none;
  margin-top: 2px;
  border-radius: 50%;
  background: var(--ok);
  box-shadow: 0 0 0 3px rgba(15, 122, 61, 0.12);
}
.chain .dn.ring {
  background: #fff;
  border: 2px solid var(--warn);
  box-shadow: 0 0 0 3px rgba(169, 96, 10, 0.14);
}
.chain .dn.hollow {
  background: #fff;
  border: 1.5px solid var(--line-2);
  box-shadow: none;
}
.dn-name {
  font-size: 12px;
  font-weight: 620;
  line-height: 1.35;
  color: var(--ink);
}
.dn-sub {
  font-size: 10.6px;
  color: var(--ink-4);
  line-height: 1.45;
  margin-top: 1px;
}

.ev-box {
  margin-top: 10px;
  padding: 7px 8px;
  border-radius: var(--r-sm);
  background: var(--paper-2);
  border: 1px dashed var(--line-2);
}
.ev-title {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--ink-4);
  margin-bottom: 3px;
}
.ev-line {
  font-family: var(--f-mono);
  font-size: 10.4px;
  line-height: 1.5;
  color: var(--ink-3);
  word-break: break-all;
}

.reject-row {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-top: 12px;
}
.ask-row {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 8px;
}
.ask-label {
  width: 96px;
  flex: none;
  font-size: 11.7px;
  color: var(--ink-3);
}

.options {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 4px;
}
.options-label {
  font-size: 11px;
  color: var(--ink-4);
}
.chip {
  border: 1px solid var(--line-2);
  background: var(--paper-2);
  border-radius: 999px;
  padding: 3px 10px;
  font: inherit;
  font-size: 11.4px;
  color: var(--ink-2);
  cursor: pointer;
}
.chip:hover {
  border-color: #a9b7f2;
  color: var(--brand);
}

.doc-foot {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 13px -15px 0;
  padding: 10px 15px;
  border-top: 1px solid var(--line);
  background: var(--paper-2);
  flex-wrap: wrap;
}
.doc-status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.4px;
  color: var(--warn);
  font-weight: 600;
}
.doc-note {
  font-size: 10.8px;
  color: var(--ink-4);
  flex: 1;
  min-width: 0;
}
.doc-foot .btn:first-of-type {
  margin-left: auto;
}
</style>
