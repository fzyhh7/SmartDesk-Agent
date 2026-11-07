<script setup lang="ts">
/**
 * 外壳：左边固定导航 + 顶部一条页头 + 主区交给路由。
 *
 * 页头只留"这是哪一页"和三个全局状态（后端通不通、MCP 工具数、当前租户），
 * 身份相关的控件全部收进左下角的身份卡 —— 原来摊在页头上一排下拉，看着像调试面板。
 */

import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'

import SideNav from '@/components/SideNav.vue'
import { useIdentity } from '@/stores/identity'
import { useUi } from '@/stores/ui'

const route = useRoute()
const identity = useIdentity()
const ui = useUi()

const title = computed(() => String(route.meta.title ?? ''))
const sub = computed(() => String(route.meta.sub ?? ''))

onMounted(() => {
  void ui.refreshAll()
})

watch(
  () => route.path,
  () => {
    void ui.refreshPending()
  },
)
</script>

<template>
  <div class="app">
    <SideNav />

    <div class="main">
      <header class="topbar">
        <div class="titles">
          <h2 class="page-title">{{ title }}</h2>
          <div class="page-sub">{{ sub }}</div>
        </div>

        <div class="meta">
          <span v-if="ui.healthy === true" class="pill ok"><i class="live" />后端在线 :8010</span>
          <span v-else-if="ui.healthy === false" class="pill bad"><i />后端未连上 :8010</span>
          <span v-else class="pill ghost">检测中…</span>
          <span class="pill accent">9 个 MCP 工具</span>
          <span class="pill ghost mono">{{ identity.tenantId }}</span>
        </div>
      </header>

      <div class="view">
        <router-view />
      </div>
    </div>
  </div>
</template>

<style scoped>
.app {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--canvas);
}

.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.topbar {
  height: 57px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 26px;
  background: var(--paper);
  border-bottom: 1px solid var(--line);
}
.titles {
  min-width: 0;
}
.page-title {
  margin: 0;
  font-size: 15px;
  font-weight: 680;
  letter-spacing: -0.015em;
  line-height: 1.3;
}
.page-sub {
  font-size: 10.6px;
  color: var(--ink-4);
  margin-top: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.meta {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 7px;
  flex: none;
}

.view {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
</style>
