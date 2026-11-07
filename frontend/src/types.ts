/** 后端返回的结构（和 `backend/app/api` 里的 schemas 对齐，只声明前端用到的字段）。 */

export type Role = 'employee' | 'approver' | 'kb_owner'

export interface Identity {
  userId: string
  tenantId: string
  roles: Role[]
}

/**
 * 引用是一条已经格式化好的字符串，例如 `[1] 星澜科技 员工手册 · 第 3 章 假期管理 · 3.1 年假`。
 * 后端 `streaming._citations()` 负责拼这个格式，前端不再二次加工。
 */
export type Citation = string

export interface ActionField {
  name: string
  label: string
  value: unknown
  source?: string
  /** 后端 `EDITABLE_BLOCK` 里的字段（如 reporter / tenant_id）为 false：改不了，也不该让用户以为能改 */
  editable?: boolean
}

/** 一条节点流水：`node` 是图里的节点名，`info` 是这一跳干了什么，`ms` 是耗时。 */
export interface TraceItem {
  node: string
  info: string
  ms?: number
}

export interface InterruptPayload {
  type: 'clarify' | 'confirm' | 'approve'
  title?: string
  fields?: ActionField[]
  citations?: Citation[]
  hint?: string
  missing?: string[]
  options?: string[]
  mode?: 'decide' | 'request'
  requested_by?: string
  required_roles?: string[]
  summary?: string
  risk?: string
}

export interface RunDetail {
  thread_id: string
  next: string[]
  paused: boolean
  interrupt: InterruptPayload | null
  outcome: string | null
  intent: string
  gate: string
  risk: string
  query: string
  reply: string
  citations: Citation[]
  view: { op?: string; label?: string; summary?: string; fields?: ActionField[]; risk?: string } | null
  approval: Record<string, unknown> | null
  ticket_no: string
  via: string
}

export interface TicketRow {
  ticket_no: string
  tenant_id: string
  title: string
  description: string
  urgency: string
  category: string
  reporter: string
  status: string
  resolution: string
  notified: number
  created_at: string
  updated_at: string
}

export interface ApprovalRow {
  id: number
  tenant_id: string
  op: string
  target: string
  risk: string
  summary: string
  requester: string
  status: string
  approver: string
  note: string
  /** 审批中心"一键通过/驳回"靠它 resume 对应会话；CLI 直连产生的记录可能为空 */
  thread_id: string
  created_at: string
  decided_at: string
  self_approved?: boolean
}

/** 问 AI 一行的展示结构（不是后端类型，只是前端状态）。 */
export interface ChatItem {
  role: 'user' | 'assistant'
  text: string
  citations: Citation[]
  streaming?: boolean
  note?: string
  tokens?: { in: number; out: number }
  /** 这条回答走过的节点（右侧面板与消息下方的 trace chips 共用） */
  nodes?: TraceItem[]
}
