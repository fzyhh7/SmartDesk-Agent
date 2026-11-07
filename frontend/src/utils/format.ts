/**
 * 展示层的翻译层：后端只给原始值（`write_irreversible`、`in_progress`、`2026-11-06 20:04:33`），
 * 一次翻译成"人话 + 颜色"，避免每个页面各写一遍映射表。
 */

export interface RiskMeta {
  key: 'read' | 'rev' | 'irr'
  text: string
  /** 风险 → 闸门：只读不过闸门，可逆走确认门，不可逆走审批门（与 action_spec.GATE_BY_RISK 一致） */
  gate: '' | 'confirm' | 'approve'
}

const RISK: Record<string, RiskMeta> = {
  read: { key: 'read', text: '只读', gate: '' },
  write_reversible: { key: 'rev', text: '可逆写', gate: 'confirm' },
  write_irreversible: { key: 'irr', text: '不可逆写', gate: 'approve' },
}

export function riskMeta(risk?: string | null): RiskMeta {
  return RISK[String(risk ?? '')] ?? { key: 'read', text: String(risk || '只读'), gate: '' }
}

export function gateText(gate?: string | null): string {
  const g = String(gate ?? '')
  if (g === 'confirm') return '本人确认'
  if (g === 'approve') return '主管审批'
  return '不过闸门'
}

const OP_LABEL: Record<string, string> = {
  query_ticket: '查工单',
  list_tickets: '列工单',
  create_ticket: '建工单',
  update_ticket: '改工单',
  close_ticket: '关工单',
  search_kb: '检索知识库',
  publish_kb_article: '发布知识文章',
}

export function opLabel(op?: string | null): string {
  return OP_LABEL[String(op ?? '')] ?? String(op ?? '-')
}

/** 一次动作的一句话描述：具体到"对哪张单做了什么"，审批人看的是这个。 */
export function actionSummary(op?: string | null, target?: string | null, summary?: string | null): string {
  if (summary) return summary
  const label = opLabel(op)
  return target ? `${label} ${target}` : label
}

const TICKET_STATUS: Record<string, { text: string; tone: string }> = {
  open: { text: '待处理', tone: 'ok' },
  in_progress: { text: '处理中', tone: 'warn' },
  closed: { text: '已关闭', tone: 'mute' },
}

export function ticketStatus(status?: string | null) {
  return TICKET_STATUS[String(status ?? '')] ?? { text: String(status ?? '-'), tone: 'mute' }
}

const URGENCY: Record<string, { text: string; tone: string }> = {
  high: { text: '高', tone: 'bad' },
  medium: { text: '中', tone: 'warn' },
  low: { text: '低', tone: 'mute' },
}

export function urgencyMeta(urgency?: string | null) {
  return URGENCY[String(urgency ?? '')] ?? { text: String(urgency ?? '-'), tone: 'mute' }
}

const APPROVAL_STATUS: Record<string, { text: string; tone: string }> = {
  pending: { text: '待处理', tone: 'warn' },
  approved: { text: '已通过', tone: 'ok' },
  edited: { text: '改后通过', tone: 'ok' },
  rejected: { text: '已驳回', tone: 'bad' },
}

export function approvalStatus(status?: string | null) {
  return APPROVAL_STATUS[String(status ?? '')] ?? { text: String(status ?? '-'), tone: 'mute' }
}

/** 后端时间形如 `2026-11-06 20:04:33`（sqlite 本地时间），iOS 的 Date 不认空格，统一换成 T。 */
export function toDate(input?: string | number | null): Date | null {
  if (input === null || input === undefined || input === '') return null
  if (typeof input === 'number') return new Date(input)
  const text = String(input).trim().replace(' ', 'T')
  const date = new Date(text)
  return Number.isNaN(date.getTime()) ? null : date
}

export function clock(input?: string | number | null): string {
  const date = toDate(input)
  if (!date) return ''
  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

/** "2 分钟前" 这种相对时间；超过一周就退回日期，避免"37 天前"这种没信息量的说法。 */
export function relTime(input?: string | number | null): string {
  const date = toDate(input)
  if (!date) return ''
  const diff = Date.now() - date.getTime()
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min} 分钟前`
  const hour = Math.floor(min / 60)
  if (hour < 24) return `${hour} 小时前`
  const day = Math.floor(hour / 24)
  if (day === 1) return '昨天'
  if (day < 7) return `${day} 天前`
  return `${date.getMonth() + 1} 月 ${date.getDate()} 日`
}

/** 停留时长（审批中心统计用），只到"分钟/小时"。 */
export function durationText(from?: string | null, to?: string | null): string {
  const start = toDate(from)
  const end = toDate(to) ?? new Date()
  if (!start) return '-'
  const min = Math.max(0, Math.round((end.getTime() - start.getTime()) / 60000))
  if (min < 60) return `${min} 分钟`
  const hour = Math.round(min / 6) / 10
  return `${hour} 小时`
}
