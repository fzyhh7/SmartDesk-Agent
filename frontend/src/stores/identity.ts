import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

import type { Identity, Role } from '@/types'

const STORAGE_KEY = 'smartdesk.identity'

/** 演示用身份模板：一个页面里切"我是谁"，才能演"员工发起 → 主管批准"。 */
export const PRESETS: Array<{ key: string; label: string; identity: Identity }> = [
  { key: 'employee', label: 'u-1001 · 普通员工', identity: { userId: 'u-1001', tenantId: 'tenant-demo', roles: ['employee'] } },
  { key: 'ops-vpn', label: 'u-2002 · 运维受理人（VPN/网络）', identity: { userId: 'u-2002', tenantId: 'tenant-demo', roles: ['employee'] } },
  { key: 'ops-fin', label: 'u-2001 · 运维受理人（财务系统）', identity: { userId: 'u-2001', tenantId: 'tenant-demo', roles: ['employee'] } },
  { key: 'approver', label: 'u-9001 · 主管（可审批）', identity: { userId: 'u-9001', tenantId: 'tenant-demo', roles: ['approver'] } },
  { key: 'kb-owner', label: 'u-3001 · 知识库 owner（可发布）', identity: { userId: 'u-3001', tenantId: 'tenant-demo', roles: ['kb_owner'] } },
  { key: 'approver-kb', label: 'u-9002 · 主管 + 知识库 owner', identity: { userId: 'u-9002', tenantId: 'tenant-demo', roles: ['approver', 'kb_owner'] } },
]

function load(): Identity {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as Identity
      if (parsed?.userId && parsed?.tenantId && Array.isArray(parsed.roles) && parsed.roles.length) {
        return parsed
      }
    }
  } catch {
    /* 本地存储坏了就直接用默认身份 */
  }
  return { ...PRESETS[0].identity, roles: [...PRESETS[0].identity.roles] }
}

export const useIdentity = defineStore('identity', () => {
  const identity = ref<Identity>(load())
  const presetKey = ref<string>(PRESETS.find((p) => p.identity.userId === identity.value.userId)?.key ?? 'custom')

  /** 三个请求头是后端唯一可信的身份来源。 */
  const headers = computed<Record<string, string>>(() => ({
    'X-User-Id': identity.value.userId,
    'X-Tenant-Id': identity.value.tenantId,
    'X-Roles': identity.value.roles.join(','),
  }))

  // 角色只有后端 guard.VALID_ROLES 认的三种（employee / approver / kb_owner），前端不另造 admin
  const isApprover = computed(() => identity.value.roles.includes('approver'))
  const canPublishKb = computed(() => identity.value.roles.includes('kb_owner'))

  /**
   * 只读快照，给"直接拿 store 用"的组件（顶栏、看板、表格）。
   * 用 storeToRefs 解构的组件仍然拿 `identity` 那一个 ref，两套写法都成立。
   */
  const userId = computed(() => identity.value.userId)
  const tenantId = computed(() => identity.value.tenantId)
  const roles = computed(() => identity.value.roles)

  function applyPreset(key: string) {
    const preset = PRESETS.find((p) => p.key === key)
    if (!preset) return
    presetKey.value = key
    identity.value = { ...preset.identity, roles: [...preset.identity.roles] }
  }

  function setRole(role: Role) {
    identity.value = { ...identity.value, roles: [role] }
    presetKey.value = 'custom'
  }

  watch(
    identity,
    (value) => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(value))
      if (presetKey.value !== 'custom' && PRESETS.find((p) => p.key === presetKey.value)?.identity.userId !== value.userId) {
        presetKey.value = 'custom'
      }
    },
    { deep: true },
  )

  return {
    identity,
    presetKey,
    headers,
    isApprover,
    canPublishKb,
    userId,
    tenantId,
    roles,
    applyPreset,
    setRole,
  }
})
