/** 外壳级状态：后端健康、待审批数量、右侧运行时面板的展开态。 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { api, checkHealth } from '@/api/client'

const RUNTIME_KEY = 'smartdesk.runtimeOpen'

export const useUi = defineStore('ui', () => {
  const healthy = ref<boolean | null>(null)
  const pending = ref(0)
  /** 运行时面板默认展开：它是这个项目最该被看见的东西（省一步点击）。 */
  const runtimeOpen = ref<boolean>(localStorage.getItem(RUNTIME_KEY) !== '0')

  function toggleRuntime() {
    runtimeOpen.value = !runtimeOpen.value
    localStorage.setItem(RUNTIME_KEY, runtimeOpen.value ? '1' : '0')
  }

  async function refreshHealth() {
    healthy.value = await checkHealth()
  }

  /** 侧栏待办角标。单个请求就够：pending 通常个位数。 */
  async function refreshPending() {
    try {
      const data = await api.approvals('pending', 50)
      pending.value = data.approvals?.length ?? 0
    } catch {
      pending.value = 0
    }
  }

  async function refreshAll() {
    await Promise.all([refreshHealth(), refreshPending()])
  }

  /** 审批中心自己拉过全量列表后直接回写角标，省一次重复请求。 */
  function setPending(count: number) {
    pending.value = count
  }

  return { healthy, pending, runtimeOpen, toggleRuntime, refreshHealth, refreshPending, refreshAll, setPending }
})
