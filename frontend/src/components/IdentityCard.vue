<script setup lang="ts">
/**
 * 身份卡：点击展开"我是谁"面板。
 *
 * 三个 header（X-User-Id / X-Tenant-Id / X-Roles）是后端唯一可信的身份来源，
 * 所以这里改的不是"界面偏好"，而是下一次请求真的换个人——演示"员工发起 → 主管审批"靠它。
 */

import { storeToRefs } from 'pinia'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import AppIcon from '@/components/AppIcon.vue'
import { PRESETS, useIdentity } from '@/stores/identity'
import { avatarText, displayName, roleTone, rolesText } from '@/utils/people'
import type { Role } from '@/types'

const store = useIdentity()
const { identity, presetKey } = storeToRefs(store)

const open = ref(false)
const root = ref<HTMLElement | null>(null)

const roles: Role[] = ['employee', 'approver', 'kb_owner']
const initials = computed(() => avatarText(identity.value.userId))
const name = computed(() => displayName(identity.value.userId))
const tone = computed(() => roleTone(identity.value.roles))

function toggle() {
  open.value = !open.value
}

function onPreset(event: Event) {
  const key = (event.target as HTMLSelectElement).value
  if (key === 'custom') {
    presetKey.value = 'custom'
    return
  }
  store.applyPreset(key)
}

function toggleRole(role: Role) {
  const now = identity.value.roles
  const next = now.includes(role) ? now.filter((item) => item !== role) : [...now, role]
  // 至少留一个角色，否则后端 guard 会一律拒绝，界面还查不出原因
  if (!next.length) return
  identity.value = { ...identity.value, roles: next }
  presetKey.value = 'custom'
}

function onDocClick(event: MouseEvent) {
  if (!open.value) return
  if (root.value && !root.value.contains(event.target as Node)) open.value = false
}

onMounted(() => document.addEventListener('mousedown', onDocClick))
onBeforeUnmount(() => document.removeEventListener('mousedown', onDocClick))
</script>

<template>
  <div ref="root" class="identity-box">
    <transition name="drop">
      <div v-if="open" class="picker panel">
        <div class="sec-label">切换身份 <span class="sp" /><span class="n">演示用，即时生效</span></div>

        <select class="select" :value="presetKey" @change="onPreset">
          <option v-for="preset in PRESETS" :key="preset.key" :value="preset.key">{{ preset.label }}</option>
          <option value="custom">自定义（下面手填）</option>
        </select>

        <label class="row">
          <span>user_id</span>
          <input v-model="identity.userId" class="input mono" spellcheck="false" />
        </label>
        <label class="row">
          <span>tenant</span>
          <input v-model="identity.tenantId" class="input mono" spellcheck="false" />
        </label>

        <div class="row roles">
          <span>roles</span>
          <div class="chips">
            <button
              v-for="role in roles"
              :key="role"
              class="chip"
              :class="{ on: identity.roles.includes(role) }"
              type="button"
              @click="toggleRole(role)"
            >
              {{ role }}
            </button>
          </div>
        </div>

        <p class="note">
          只有后端 <b class="mono">guard.VALID_ROLES</b> 认的三种角色；发起人不能批准自己的单。
        </p>
      </div>
    </transition>

    <button class="identity" type="button" :aria-expanded="open" @click="toggle">
      <span class="avatar" :class="tone">{{ initials }}</span>
      <span class="who">
        <span class="who-name">{{ name }}</span>
        <span class="who-role">{{ rolesText(identity.roles) }} · {{ identity.tenantId }}</span>
      </span>
      <AppIcon class="chev" name="chevronDown" :size="14" />
    </button>
  </div>
</template>

<style scoped>
.identity-box {
  position: relative;
}

.identity {
  display: flex;
  align-items: center;
  gap: 9px;
  width: 100%;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--paper-2);
  cursor: pointer;
  text-align: left;
  font: inherit;
  color: var(--ink);
  transition: 0.13s;
}
.identity:hover {
  border-color: var(--line-2);
  background: #fff;
  box-shadow: var(--sh-1);
}

.avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  flex: none;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 700;
  background: var(--brand-tint);
  color: var(--brand);
  box-shadow: inset 0 0 0 1px var(--brand-line);
}
.avatar.warn {
  background: var(--warn-tint);
  color: var(--warn);
  box-shadow: inset 0 0 0 1px var(--warn-line);
}
.avatar.ok {
  background: var(--ok-tint);
  color: var(--ok);
  box-shadow: inset 0 0 0 1px var(--ok-line);
}

.who {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.who-name {
  font-size: 12.2px;
  font-weight: 650;
  line-height: 1.3;
}
.who-role {
  font-size: 10.4px;
  color: var(--ink-4);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chev {
  margin-left: auto;
  color: var(--ink-4);
}

.picker {
  position: absolute;
  left: 0;
  right: 0;
  bottom: calc(100% + 8px);
  padding: 12px;
  z-index: 30;
  box-shadow: var(--sh-2);
  background: var(--paper);
}

.select,
.input {
  width: 100%;
  height: 29px;
  padding: 0 9px;
  border: 1px solid var(--line-2);
  border-radius: 8px;
  background: #fff;
  color: var(--ink);
  font: inherit;
  font-size: 12.1px;
}
.select {
  margin-bottom: 8px;
  cursor: pointer;
}
.input:focus,
.select:focus {
  outline: 0;
  border-color: #a9b7f2;
  box-shadow: 0 0 0 3px rgba(58, 86, 212, 0.09);
}

.row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 7px;
}
.row > span {
  width: 54px;
  flex: none;
  font-size: 11.4px;
  color: var(--ink-4);
}
.row.roles {
  align-items: flex-start;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.chip {
  font: inherit;
  font-size: 10.8px;
  font-weight: 620;
  padding: 3px 8px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: var(--paper-2);
  color: var(--ink-3);
  cursor: pointer;
  transition: 0.12s;
}
.chip.on {
  background: var(--brand-tint);
  border-color: var(--brand-line);
  color: var(--brand);
}

.note {
  margin: 9px 0 0;
  font-size: 10.6px;
  line-height: 1.5;
  color: var(--ink-4);
}
.note b {
  font-weight: 620;
  color: var(--ink-3);
}

.drop-enter-active,
.drop-leave-active {
  transition: opacity 0.14s, transform 0.14s;
}
.drop-enter-from,
.drop-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
