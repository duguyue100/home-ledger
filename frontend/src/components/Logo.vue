<script setup lang="ts">
defineProps<{ size?: number; withText?: boolean }>()
</script>

<template>
  <span style="display:inline-flex;align-items:center;gap:8px">
    <svg :width="size ?? 22" :height="size ?? 22" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#2d6a4f" />
      <path d="M16 7 L25 15 L22 15 L22 24 L10 24 L10 15 L7 15 Z" fill="#ffffff" />
      <rect x="14.5" y="18" width="3" height="6" fill="#2d6a4f" />
      <path d="M11 22 L21 22" stroke="#2d6a4f" stroke-width="0.9" opacity="0.45" />
    </svg>
    <span v-if="withText" style="font-weight:600;font-size:15px;letter-spacing:-0.01em">Home Ledger</span>
  </span>
</template>