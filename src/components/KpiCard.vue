<script setup>
defineProps({
  label: String,
  value: String,
  sub: String,
  cta: { type: String, default: 'Voir le détail' },
})
defineEmits(['activate'])
</script>

<template>
  <button class="kpi" @click="$emit('activate')">
    <div class="label">{{ label }}</div>
    <div class="value num">{{ value }}</div>
    <div v-if="sub" class="sub">{{ sub }}</div>
    <div class="cta">{{ cta }} →</div>
  </button>
</template>
