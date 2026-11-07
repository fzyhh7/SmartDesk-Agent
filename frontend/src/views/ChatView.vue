<script setup lang="ts">
/**
 * 会话工作台。
 *
 * 三块：左边聊天（人说话）、中间闸门卡片（AI 要写之前停下来等人）、右边运行时（机器在干什么）。
 * 演示时讲解顺序就是这三块的顺序：问一句 → 停一下 → 看一眼状态机停在哪。
 */

import MarkdownIt from 'markdown-it'
import { ElMessage } from 'element-plus'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppIcon from '@/components/AppIcon.vue'
import GateCard from '@/components/GateCard.vue'
import RuntimePanel from '@/components/RuntimePanel.vue'
import { api } from '@/api/client'
import { chatStream, resumeStream } from '@/api/sse'
import type { StreamEvent } from '@/api/sse'
import { useIdentity } from '@/stores/identity'
import { useSessions } from '@/stores/sessions'
import { useUi } from '@/stores/ui'
import { clock } from '@/utils/format'
import type { ChatItem, InterruptPayload, RunDetail, TraceItem } from '@/types'

const md = new MarkdownIt({ html: false, linkify: true, breaks: true })

const identity = useIdentity()
const sessions = useSessions()
const ui = useUi()
const router = useRouter()
const route = useRoute()

const items = ref<ChatItem[]>([])
const detail = ref<RunDetail | null>(null)
const interrupt = ref<InterruptPayload | null>(null)
const trace = ref<TraceItem[]>([])
const tokens = ref<{ in: number; out: number } | null>(null)
const elapsedMs = ref<number | null>(null)
const running = ref(false)
const draft = ref('')
const listRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLTextAreaElement | null>(null)

let controller: AbortController | null = null
let loadSeq = 0

/** 节点名 → 中文短标签（trace chips 和节点事件共用一套说法）。 */
const NODE_LABEL: Record<string, string> = {
  classify_request: '理解',
  gather_evidence: '取证',
  answer_with_citations: '作答',
  plan_action: '规划',
  ask_missing_info: '澄清',
  confirm_action: '确认',
  approve_action: '审批',
  execute_action: '执行',
  compose_reply: '回复',
}

const threadId = computed(() => detail.value?.thread_id || sessions.current)

const status = computed(() => {
  if (running.value) return { tone: 'accent', text: '进行中' }
  const it = interrupt.value
  if (it) {
    if (it.type === 'approve') return { tone: 'warn', text: '等待审批' }
    if (it.type === 'confirm') return { tone: 'warn', text: '等待确认' }
    return { tone: 'warn', text: '等待补充' }
  }
  if (detail.value) return { tone: 'ok', text: '已完成' }
  return { tone: 'ghost', text: '空闲' }
})

const showWelcome = computed(() => !items.value.length && !interrupt.value)

/** 最后一条回复的状态徽章：停在闸门上时不该显示"已回复"。 */
const tailPill = computed(() => {
  const it = interrupt.value
  if (it?.type === 'approve') return { tone: 'warn', text: '等待审批' }
  if (it?.type === 'confirm') return { tone: 'warn', text: '等待确认' }
  if (it) return { tone: 'warn', text: '等待补充' }
  return { tone: 'ok', text: '已回复' }
})

const CAPS = [
  {
    icon: 'book',
    title: '知识问答',
    desc: '7 份制度、97 个切片，双路混合召回 + 精排，回答必带引用。',
    foot: 'Recall@3 98.0% · 引用准确率 100%',
  },
  {
    icon: 'shield',
    title: '受控执行',
    desc: '9 节点状态机，写操作按风险分三级，唯一的写节点在最后。',
    foot: '读 / 可逆写 / 不可逆写',
  },
  {
    icon: 'check',
    title: '审批留痕',
    desc: '发起≠批准，恢复时按恢复人身份二次鉴权，自审会被标记。',
    foot: 'approvals 每次决策落库',
  },
]

const EXAMPLES = [
  { icon: 'book', text: '年假有多少天？', badge: '知识检索', tone: 'ok', note: '带引用回答' },
  { icon: 'ticket', text: '帮我建个工单：会议室投影仪没信号', badge: '需要确认', tone: 'warn', note: '本人点一下才写' },
  { icon: 'lock', text: '把 TK-20261106-0005 关掉并通知提单人', badge: '需要审批', tone: 'bad', note: '通知外发不可撤回' },
  { icon: 'search', text: '帮我查一下我上一张工单', badge: '直接查', tone: 'ghost', note: '只读，不需要闸门' },
]

function render(text: string): string {
  return md.render(text || '')
}

function pushAssistant(text = ''): ChatItem {
  const item: ChatItem = { role: 'assistant', text, citations: [], streaming: true, nodes: [] }
  items.value.push(item)
  return items.value[items.value.length - 1]
}

function lastAssistant(): ChatItem | undefined {
  for (let i = items.value.length - 1; i >= 0; i -= 1) {
    if (items.value[i].role === 'assistant') return items.value[i]
  }
  return undefined
}

async function scrollDown() {
  await nextTick()
  const el = listRef.value
  if (el) el.scrollTop = el.scrollHeight
}

function nodeInfo(data: Record<string, unknown>): string {
  if (typeof data.evidence_count === 'number') return `检索到 ${data.evidence_count} 条依据`
  if (typeof data.facts_count === 'number') return `${data.facts_count} 条工单事实`
  if (typeof data.intent === 'string') return `intent = ${data.intent}`
  if (typeof data.risk === 'string') return `risk = ${data.risk}`
  if (typeof data.outcome === 'string') return `outcome = ${data.outcome}`
  return ''
}

function handleEvent(evt: StreamEvent) {
  const data = (evt.data ?? {}) as Record<string, any>
  const last = lastAssistant()
  if (evt.event === 'node' && typeof data.node === 'string') {
    const node = String(data.node)
    const item: TraceItem = { node, info: nodeInfo(data), ms: typeof data.ms === 'number' ? data.ms : undefined }
    trace.value = [...trace.value, item]
    if (last) last.nodes = [...(last.nodes ?? []), item]
    return
  }
  if (evt.event === 'token') {
    if (last) {
      last.text += String(data.text ?? '')
      last.streaming = true
    }
    void scrollDown()
    return
  }
  if (evt.event === 'interrupt') {
    const payloads = Array.isArray(data.payloads) ? data.payloads : []
    interrupt.value = (payloads[0] ?? null) as InterruptPayload | null
    if (last) last.streaming = false
    if (typeof data.elapsed_ms === 'number') elapsedMs.value = data.elapsed_ms
    if (data.tokens) tokens.value = data.tokens as { in: number; out: number }
    void scrollDown()
    return
  }
  if (evt.event === 'done') {
    if (last) {
      last.text = String(data.reply ?? last.text ?? '')
      last.citations = Array.isArray(data.citations) ? (data.citations as string[]) : []
      last.streaming = false
      last.tokens = (data.tokens as { in: number; out: number }) ?? undefined
      const bits: string[] = []
      if (data.via) bits.push(`via ${data.via}`)
      if (data.ticket_no) bits.push(`单号 ${data.ticket_no}`)
      last.note = bits.join(' · ')
    }
    if (typeof data.elapsed_ms === 'number') elapsedMs.value = data.elapsed_ms
    if (data.tokens) tokens.value = data.tokens as { in: number; out: number }
    void scrollDown()
    return
  }
  if (evt.event === 'error') {
    if (last) {
      last.streaming = false
      last.text = last.text || `出错了：${String(data.message ?? '未知错误')}`
    }
  }
}

function cleanup() {
  interrupt.value = null
  trace.value = []
  tokens.value = null
}

async function send(text?: string) {
  const content = (text ?? draft.value).trim()
  if (!content || running.value) return
  const thread = sessions.ensure()

  draft.value = ''
  cleanup()
  items.value.push({ role: 'user', text: content, citations: [] })
  pushAssistant()
  sessions.titleFrom(thread, content)
  sessions.update(thread, { state: 'running' })
  running.value = true
  elapsedMs.value = null
  await scrollDown()

  controller = new AbortController()
  try {
    await chatStream(content, thread, identity.headers, { onEvent: handleEvent, signal: controller.signal })
  } catch (err) {
    onStreamError(err)
  } finally {
    await finish(thread)
  }
}

/** 闸门卡片提交：clarify 发 answers，confirm/approve 发 decision；都走同一条 thread 的 resume。 */
async function onGateSubmit(body: Record<string, unknown>) {
  const thread = sessions.current
  if (!thread || running.value) return

  interrupt.value = null
  sessions.update(thread, { state: 'running' })
  pushAssistant()
  running.value = true
  elapsedMs.value = null
  await scrollDown()

  controller = new AbortController()
  try {
    await resumeStream(thread, body, identity.headers, { onEvent: handleEvent, signal: controller.signal })
  } catch (err) {
    onStreamError(err)
  } finally {
    await finish(thread)
  }
}

function onStreamError(err: unknown) {
  const text = err instanceof Error ? err.message : String(err)
  const last = lastAssistant()
  if (text.includes('HTTP 409')) {
    ElMessage.warning(text.replace(/^HTTP 409：/, ''))
    if (last && !last.text) last.text = '这条会话还停在待办卡片上，先处理卡片（或点"新会话"另起一条）。'
  } else if ((err as Error)?.name === 'AbortError') {
    if (last) last.text = last.text || '已停止。'
  } else {
    ElMessage.error(text)
    if (last && !last.text) last.text = `请求失败：${text}`
  }
  if (last) last.streaming = false
}

async function finish(thread: string) {
  running.value = false
  controller = null
  const last = lastAssistant()
  if (last) last.streaming = false
  sessions.update(thread, { state: interrupt.value ? 'paused' : 'done' })
  await refreshDetail(thread)
  void ui.refreshPending()
  await scrollDown()
}

async function refreshDetail(thread = ''): Promise<void> {
  const id = thread || sessions.current
  if (!id) return
  try {
    const data = await api.run(id)
    detail.value = data
    interrupt.value = data.interrupt ?? null
    if (data.paused) sessions.update(id, { state: 'paused' })
  } catch {
    /* 刚建但还没跑过的 thread 没有 checkpoint，404 是正常的 */
  }
}

async function loadThread(thread: string) {
  // 切会话时会有两次并发拉取（onMounted 一次、watch(sessions.current) 一次），
  // 用序号把旧请求的返回丢掉，否则气泡会被追加两遍。
  const mine = ++loadSeq
  items.value = []
  cleanup()
  detail.value = null
  elapsedMs.value = null
  if (!thread) {
    sessions.start()
    return
  }
  await refreshDetail(thread)
  if (mine !== loadSeq) return
  // 从 checkpoint 恢复的会话：把它当时说的话和已经产出的回复也放回气泡里，
  // 否则打开一条会话链接只看到一张卡片，看不出上下文。
  if (detail.value?.query) {
    items.value.push({ role: 'user', text: detail.value.query, citations: [], nodes: [] })
  }
  if (interrupt.value) {
    items.value.push({
      role: 'assistant',
      text: '这条会话还停在闸门上（从服务端 checkpoint 恢复的），下面是待你处理的卡片。',
      citations: [],
      nodes: [],
    })
  } else if (detail.value?.reply) {
    items.value.push({
      role: 'assistant',
      text: detail.value.reply,
      citations: detail.value.citations ?? [],
      nodes: [],
    })
  }
  await scrollDown()
}

function newSession() {
  stop()
  sessions.start()
  void loadThread(sessions.current)
  inputRef.value?.focus()
}

function stop() {
  controller?.abort()
  controller = null
  running.value = false
}

function useExample(text: string) {
  draft.value = text
  inputRef.value?.focus()
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
  event.preventDefault()
  void send()
}

watch(
  () => sessions.current,
  (thread) => {
    if (!running.value) void loadThread(thread)
  },
)

onMounted(() => {
  // ?thread=xxx 是"别人发给我的一条会话"：本地没有就补进列表，再按服务端 checkpoint 恢复
  const linked = typeof route.query.thread === 'string' ? route.query.thread.trim() : ''
  if (linked) sessions.adopt(linked)
  const thread = linked || sessions.ensure()
  void loadThread(thread)
})

onBeforeUnmount(() => {
  stop()
})
</script>

<template>
  <div class="chat">
    <div class="chat-col">
      <header class="chat-head">
        <span class="thread">
          <AppIcon name="chat" :size="12" />
          <span class="mono">{{ threadId || '新会话' }}</span>
        </span>
        <span class="pill" :class="status.tone">
          <i v-if="running" class="live" />
          {{ status.text }}
        </span>
        <span class="spacer" />
        <button type="button" class="btn ghost sm" @click="newSession">
          <AppIcon name="plus" :size="13" /> 新会话
        </button>
        <button v-if="running" type="button" class="btn ghost sm" @click="stop">
          <AppIcon name="stop" :size="12" /> 停止
        </button>
        <button type="button" class="btn ghost sm" :title="ui.runtimeOpen ? '收起运行时面板' : '展开运行时面板'" @click="ui.toggleRuntime()">
          <AppIcon name="code" :size="13" />
        </button>
      </header>

      <div class="chat-body">
        <!-- 首屏：新会话时把"能干什么"和"闸门长什么样"提前讲清楚 -->
        <div v-if="showWelcome" class="welcome-wrap">
          <div class="welcome">
            <div class="hero-mark"><AppIcon name="spark" :size="22" /></div>
            <div class="eyebrow">{{ identity.tenantId || 'tenant-demo' }} · IT 服务台</div>
            <h1>今天要处理什么？</h1>
            <p class="lede">
              我能查制度、查工单、建单和关单。所有写操作都会先给你一张单据确认；涉及外发或不可回滚的动作，会转给主管审批
              —— 每一步都有留痕，可以跨进程接着跑。
            </p>

            <div class="caps">
              <div v-for="cap in CAPS" :key="cap.title" class="cap">
                <span class="cap-icon"><AppIcon :name="cap.icon" :size="13" /></span>
                <div class="cap-title">{{ cap.title }}</div>
                <p class="cap-desc">{{ cap.desc }}</p>
                <div class="cap-foot">{{ cap.foot }}</div>
              </div>
            </div>

            <div class="ex-head">
              <span class="sec-label">试试这些</span>
              <span class="ex-hint">点一下填进输入框</span>
            </div>
            <div class="examples">
              <button v-for="ex in EXAMPLES" :key="ex.text" type="button" class="example" @click="useExample(ex.text)">
                <span class="ex-icon"><AppIcon :name="ex.icon" :size="12" /></span>
                <span class="ex-body">
                  <span class="ex-text">{{ ex.text }}</span>
                  <span class="ex-meta">
                    <span class="pill" :class="ex.tone">{{ ex.badge }}</span>
                    <span class="ex-note">{{ ex.note }}</span>
                  </span>
                </span>
              </button>
            </div>
          </div>
        </div>

        <div v-else ref="listRef" class="chat-scroll">
          <div class="chat-inner">
            <div v-for="(item, index) in items" :key="index" class="msg" :class="{ me: item.role === 'user' }">
              <template v-if="item.role === 'user'">
                <div class="bubble-me">{{ item.text }}</div>
              </template>
              <template v-else>
                <div class="avatar"><AppIcon name="spark" :size="13" /></div>
                <div class="msg-body">
                  <div class="speaker">
                    <span class="who">SmartDesk</span>
                    <span class="when">{{ clock(Date.now()) }}</span>
                    <span
                      v-if="!item.streaming && !running && item === items[items.length - 1]"
                      class="pill"
                      :class="tailPill.tone"
                      >{{ tailPill.text }}</span
                    >
                  </div>
                  <div v-if="item.text" class="answer" v-html="render(item.text)" />
                  <span v-else-if="item.streaming" class="typing"><i /><i /><i /></span>

                  <div v-if="item.citations.length" class="cites">
                    <div class="cites-head">
                      <AppIcon name="book" :size="11" /> 引用 · {{ item.citations.length }} 条
                    </div>
                    <ol class="cites-list">
                      <li v-for="citation in item.citations" :key="citation">{{ citation }}</li>
                    </ol>
                  </div>

                  <div v-if="item.nodes?.length" class="trace">
                    <span v-for="traceItem in item.nodes" :key="traceItem.node" class="trace-item">
                      <AppIcon name="check" :size="10" />
                      {{ NODE_LABEL[traceItem.node] ?? traceItem.node }}
                      <span v-if="traceItem.ms" class="mono">{{ (traceItem.ms / 1000).toFixed(1) }}s</span>
                    </span>
                    <span v-if="item.note" class="trace-note">{{ item.note }}</span>
                  </div>
                </div>
              </template>
            </div>

            <GateCard
              v-if="interrupt"
              :payload="interrupt"
              :disabled="running"
              @submit="onGateSubmit"
              @approvals="router.push('/approvals')"
            />
          </div>
        </div>
      </div>

      <footer class="composer">
        <div class="composer-box">
          <textarea
            ref="inputRef"
            v-model="draft"
            class="composer-input"
            rows="2"
            placeholder="说一句话，比如：发票怎么开？/ 帮我建个工单：会议室投影仪没信号"
            @keydown="onKeydown"
          />
          <div class="composer-foot">
            <div class="quick">
              <button type="button" class="chip" @click="useExample('年假有多少天？')">年假有多少天</button>
              <button type="button" class="chip" @click="useExample('建单：VPN 连不上')">建单：VPN 连不上</button>
              <button type="button" class="chip" @click="useExample('关掉上一张工单')">关掉上一张工单</button>
            </div>
            <span class="key-hint"><kbd>Enter</kbd> 发送 · <kbd>Shift</kbd> + <kbd>Enter</kbd> 换行</span>
            <button v-if="!running" type="button" class="btn primary" :disabled="!draft.trim()" @click="send()">
              发送
            </button>
            <button v-else type="button" class="btn danger" @click="stop">停止</button>
          </div>
        </div>
      </footer>
    </div>

    <RuntimePanel
      v-if="ui.runtimeOpen"
      :detail="detail"
      :nodes="trace"
      :running="running"
      :elapsed-ms="elapsedMs"
      :tokens="tokens"
    />
  </div>
</template>

<style scoped>
.chat {
  flex: 1;
  min-height: 0;
  display: flex;
}
.chat-col {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.chat-head {
  height: 44px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 18px;
  border-bottom: 1px solid var(--line);
  background: var(--paper);
}
.thread {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--paper-2);
  color: var(--ink-3);
  font-size: 10.6px;
}
.spacer {
  flex: 1;
}

.chat-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.welcome-wrap {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow-y: auto;
}
.welcome {
  max-width: 792px;
  width: 100%;
  margin: auto;
  padding: 30px 26px 26px;
  animation: fade 0.3s ease;
}
.hero-mark {
  width: 44px;
  height: 44px;
  border-radius: 13px;
  display: grid;
  place-items: center;
  color: #fff;
  background: linear-gradient(145deg, #5b74ea, #3a56d4 58%, #2c43ad);
  box-shadow: 0 6px 18px rgba(58, 86, 212, 0.28), inset 0 1px 0 rgba(255, 255, 255, 0.26);
}
.eyebrow {
  margin-top: 14px;
  font-size: 10.4px;
  font-weight: 700;
  letter-spacing: 0.11em;
  color: var(--ink-4);
  text-transform: uppercase;
}
h1 {
  margin: 7px 0 0;
  font-size: 25px;
  letter-spacing: -0.025em;
  font-weight: 700;
}
.lede {
  margin: 9px 0 0;
  font-size: 12.8px;
  line-height: 1.72;
  color: var(--ink-3);
  max-width: 640px;
}

.caps {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-top: 20px;
}
.cap {
  border: 1px solid var(--line);
  border-radius: var(--r);
  padding: 12px 13px 10px;
  background: var(--paper);
  box-shadow: var(--sh-1);
}
.cap-icon {
  width: 24px;
  height: 24px;
  border-radius: 7px;
  display: grid;
  place-items: center;
  background: var(--brand-tint);
  color: var(--brand);
}
.cap-title {
  margin-top: 9px;
  font-size: 12.6px;
  font-weight: 660;
}
.cap-desc {
  margin: 4px 0 0;
  font-size: 11.2px;
  line-height: 1.6;
  color: var(--ink-3);
}
.cap-foot {
  margin-top: 9px;
  padding-top: 8px;
  border-top: 1px dashed var(--line);
  font-family: var(--f-mono);
  font-size: 9.9px;
  color: var(--ink-4);
}

.ex-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 22px;
}
.ex-hint {
  font-size: 10.4px;
  color: var(--ink-4);
}
.examples {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 9px;
  margin-top: 9px;
}
.example {
  display: flex;
  gap: 9px;
  text-align: left;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--paper);
  font: inherit;
  cursor: pointer;
  transition: border-color 0.13s, box-shadow 0.13s, transform 0.13s;
}
.example:hover {
  border-color: #b9c4f4;
  box-shadow: var(--sh-2);
  transform: translateY(-1px);
}
.ex-icon {
  width: 21px;
  height: 21px;
  flex: none;
  border-radius: 6px;
  display: grid;
  place-items: center;
  background: var(--paper-2);
  color: var(--ink-3);
  border: 1px solid var(--line);
}
.ex-body {
  min-width: 0;
}
.ex-text {
  display: block;
  font-size: 12.2px;
  font-weight: 560;
  color: var(--ink);
  line-height: 1.45;
}
.ex-meta {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 6px;
}
.ex-note {
  font-size: 10.3px;
  color: var(--ink-4);
}

.chat-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.chat-inner {
  max-width: 740px;
  margin: 0 auto;
  padding: 18px 26px 10px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.msg {
  display: flex;
  gap: 9px;
  animation: rise 0.22s ease;
}
.msg.me {
  justify-content: flex-end;
}
.avatar {
  width: 25px;
  height: 25px;
  flex: none;
  border-radius: 8px;
  display: grid;
  place-items: center;
  color: #fff;
  background: linear-gradient(145deg, #5b74ea, #3a56d4 60%, #2c43ad);
  box-shadow: 0 2px 6px rgba(58, 86, 212, 0.26);
}
.msg-body {
  min-width: 0;
  flex: 1;
}
.speaker {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 5px;
}
.who {
  font-size: 12.2px;
  font-weight: 660;
}
.when {
  font-family: var(--f-mono);
  font-size: 10px;
  color: var(--ink-4);
}
.answer {
  font-size: 13px;
  line-height: 1.78;
  color: var(--ink);
  word-break: break-word;
}
.answer :deep(p) {
  margin: 0 0 8px;
}
.answer :deep(p:last-child) {
  margin-bottom: 0;
}
.answer :deep(strong) {
  font-weight: 660;
}
.answer :deep(code) {
  font-family: var(--f-mono);
  font-size: 11.6px;
  background: var(--paper-2);
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 1px 5px;
}
.answer :deep(ul),
.answer :deep(ol) {
  margin: 0 0 8px;
  padding-left: 20px;
}
.answer :deep(li) {
  margin: 3px 0;
}

.bubble-me {
  max-width: 78%;
  padding: 9px 13px;
  border-radius: 14px 14px 4px 14px;
  background: linear-gradient(180deg, #eef2fe, #e4ebfd);
  border: 1px solid #ccd8f9;
  font-size: 12.8px;
  line-height: 1.65;
  color: #1f2a44;
}

.typing {
  display: inline-flex;
  gap: 3px;
  padding: 6px 0;
}
.typing i {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--ink-4);
  animation: pulse 1.2s ease-in-out infinite;
}
.typing i:nth-child(2) {
  animation-delay: 0.16s;
}
.typing i:nth-child(3) {
  animation-delay: 0.32s;
}

.cites {
  margin-top: 9px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--paper-2);
  padding: 8px 10px;
}
.cites-head {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 10.2px;
  font-weight: 660;
  letter-spacing: 0.03em;
  color: var(--ink-4);
}
.cites-list {
  margin: 5px 0 0;
  padding: 0;
  list-style: none;
}
.cites-list li {
  font-family: var(--f-mono);
  font-size: 10.5px;
  line-height: 1.7;
  color: var(--ink-3);
}

.trace {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 10px;
  padding-top: 9px;
  border-top: 1px dashed var(--line);
}
.trace-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10.2px;
  color: var(--ink-3);
  background: var(--paper-2);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 1.5px 7px;
}
.trace-item .mono {
  color: var(--ink-4);
  font-size: 9.6px;
}
.trace-note {
  font-size: 10.2px;
  color: var(--ink-4);
}

.composer {
  flex: none;
  padding: 10px 26px 14px;
  background: var(--paper);
  border-top: 1px solid var(--line);
}
.composer-box {
  max-width: 740px;
  margin: 0 auto;
  border: 1px solid var(--line-2);
  border-radius: var(--r);
  background: var(--paper);
  box-shadow: var(--sh-1);
  transition: border-color 0.14s, box-shadow 0.14s;
}
.composer-box:focus-within {
  border-color: #a9b7f2;
  box-shadow: 0 0 0 3px rgba(58, 86, 212, 0.09);
}
.composer-input {
  display: block;
  width: 100%;
  border: 0;
  outline: 0;
  resize: none;
  background: transparent;
  font: inherit;
  font-size: 13px;
  line-height: 1.7;
  color: var(--ink);
  padding: 10px 13px 2px;
}
.composer-input::placeholder {
  color: var(--ink-4);
}
.composer-foot {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 9px 8px;
}
.quick {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
  min-width: 0;
}
.key-hint {
  margin-left: auto;
  font-size: 10px;
  color: var(--ink-4);
  white-space: nowrap;
}
</style>
