/**
 * 演示账号的显示名。
 *
 * 后端只认 user_id（`X-User-Id` 头），不存姓名——权限判断从不需要名字。
 * 界面上光秃秃显示 `u-1001` 太冷，所以这里放一张"演示用"的昵称表；
 * 查不到就退回 user_id 本身，不会因此丢信息。
 */

const NAMES: Record<string, string> = {
  'u-1001': '陈晓',
  'u-2001': '周涛',
  'u-2002': '王一诺',
  'u-3001': '王珂',
  'u-9001': '李敏',
  'u-9002': '李敏',
}

export function displayName(userId?: string | null): string {
  const id = String(userId ?? '').trim()
  if (!id) return '未登录'
  return NAMES[id] ?? id
}

export function avatarText(userId?: string | null): string {
  const name = displayName(userId)
  return name.slice(0, 1).toUpperCase()
}

const ROLE_TEXT: Record<string, string> = {
  employee: '员工',
  approver: '主管',
  kb_owner: '知识库 owner',
}

export function rolesText(roles?: string[] | null): string {
  const list = (roles ?? []).map((role) => ROLE_TEXT[role] ?? role)
  return list.length ? list.join(' · ') : '无角色'
}

/** 头像配色：主管用琥珀、知识库 owner 用绿，普通员工用品牌色。 */
export function roleTone(roles?: string[] | null): 'brand' | 'warn' | 'ok' {
  if (roles?.includes('approver')) return 'warn'
  if (roles?.includes('kb_owner')) return 'ok'
  return 'brand'
}
