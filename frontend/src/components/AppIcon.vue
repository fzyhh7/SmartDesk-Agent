<script setup lang="ts">
/**
 * 线性图标集（24×24 stroke）。全部内联，避免为了几个图标引一整个图标库。
 * 用法：<AppIcon name="shield" :size="16" />
 */

withDefaults(defineProps<{ name: string; size?: number }>(), { size: 16 })

const PATHS: Record<string, string> = {
  chat: 'M21 11.6a8.6 8.6 0 0 1-8.7 8.6 9 9 0 0 1-3.9-.9L3.2 21l1.8-5a8.5 8.5 0 0 1-1-4A8.6 8.6 0 0 1 12.6 3 8.6 8.6 0 0 1 21 11.6z',
  shield: 'M12 3l7 3v5.6c0 4.2-2.9 7.6-7 9.4-4.1-1.8-7-5.2-7-9.4V6l7-3z',
  ticket: 'M20.6 12.6l-8 8L3 11V3h8l9.6 9.6zM7.6 7.6h.01',
  plus: 'M12 5v14M5 12h14',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM20.5 20.5L16.5 16.5',
  book: 'M4 5.6A2.6 2.6 0 0 1 6.6 3H19v18H6.6A2.6 2.6 0 0 1 4 18.4v-12.8zM19 16H6.6',
  spark: 'M12 3l1.9 4.7L18.6 9.6l-4.7 1.9L12 16.2l-1.9-4.7L5.4 9.6l4.7-1.9L12 3z',
  check: 'M5 12.5l4.6 4.5L19 7.2',
  alert: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 8v4.8M12 16.4h.01',
  lock: 'M6.5 11V8.2a5.5 5.5 0 0 1 11 0V11M4.5 11h15v9.5h-15z',
  send: 'M4 12l16-8-6.2 16-3.4-6.4L4 12z',
  refresh: 'M20.2 11.2A8.2 8.2 0 1 0 18 17.4M20.2 5v6.2H14',
  close: 'M6.5 6.5l11 11M17.5 6.5l-11 11',
  chevron: 'M9.5 6l6 6-6 6',
  chevronDown: 'M6 9.5l6 6 6-6',
  user: 'M12 12.2a4.1 4.1 0 1 0 0-8.2 4.1 4.1 0 0 0 0 8.2zM4.6 21a7.4 7.4 0 0 1 14.8 0',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7.8v4.6l3.2 1.9',
  code: 'M9.2 8L5 12l4.2 4M14.8 8l4.2 4-4.2 4',
  stop: 'M7.5 7.5h9v9h-9z',
  filter: 'M4 6.5h16M4 12h10M4 17.5h6',
  pound: 'M9.5 3.5L7.5 20.5M16.5 3.5l-2 17M4.5 9h15M3.8 15h15',
  chevronLeft: 'M14.5 6l-6 6 6 6',
  dot: 'M12 10v.01M12 14v.01',
}

const PATHS_FALLBACK = 'M12 8v.01M12 12v4'
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="PATHS[name] ?? PATHS_FALLBACK" />
  </svg>
</template>
