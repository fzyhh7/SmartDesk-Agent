/** HTTP 客户端：只做"带身份请求头 + 解析 JSON + 报错"，不含任何业务判断。 */

import { useIdentity } from '@/stores/identity'
import type { ApprovalRow, RunDetail, TicketRow } from '@/types'

const BASE = '/api/v1'

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const identity = useIdentity()
  const resp = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...identity.headers,
      ...(init.headers ?? {}),
    },
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`HTTP ${resp.status}：${text || resp.statusText}`)
  }
  return (await resp.json()) as T
}

export const api = {
  tickets(status = '', limit = 20): Promise<{ ok: boolean; count: number; tickets: TicketRow[] }> {
    const query = new URLSearchParams({ status, limit: String(limit) })
    return request(`/tickets?${query.toString()}`)
  },

  approvals(status = '', limit = 50): Promise<{ ok: boolean; approvals: ApprovalRow[] }> {
    const query = new URLSearchParams({ status, limit: String(limit) })
    return request(`/approvals?${query.toString()}`)
  },

  run(threadId: string): Promise<RunDetail> {
    return request(`/runs/${encodeURIComponent(threadId)}`)
  },

}

/** 健康检查在根路径（不带 /api/v1 前缀），单独写一个。 */
export async function checkHealth(): Promise<boolean> {
  try {
    const resp = await fetch('/health')
    return resp.ok
  } catch {
    return false
  }
}
