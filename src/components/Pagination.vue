<script setup>
import { computed } from 'vue'
const props = defineProps({
  page: { type: Number, required: true },
  pageSize: { type: Number, required: true },
  total: { type: Number, required: true },
})
const emit = defineEmits(['update:page'])
const pages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))
const from = computed(() => (props.total === 0 ? 0 : (props.page - 1) * props.pageSize + 1))
const to = computed(() => Math.min(props.total, props.page * props.pageSize))
</script>

<template>
  <div class="pagination" v-if="total > pageSize">
    <button :disabled="page <= 1" @click="emit('update:page', page - 1)">← Précédent</button>
    <span class="info num">{{ from }}–{{ to }} sur {{ total }}</span>
    <button :disabled="page >= pages" @click="emit('update:page', page + 1)">Suivant →</button>
  </div>
</template>
