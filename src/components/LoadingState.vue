<script setup>
defineProps({ message: { type: String, default: 'Chargement…' } })
</script>

<template>
  <div class="empty loading-state" role="status" aria-live="polite">
    <div class="spinner" aria-hidden="true"></div>
    <div>{{ message }}</div>
  </div>
</template>
