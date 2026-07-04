<script setup>
import { formatEurFull, TYPE_LABELS } from '../lib/format.js'
defineProps({ record: { type: Object, required: true } })
</script>

<template>
  <div class="row">
    <div>
      <router-link class="nom" :to="`/beneficiaire/${encodeURIComponent(record.beneficiaire.id)}`">
        {{ record.beneficiaire.nom }}
      </router-link>
      <div class="meta" style="margin-top:4px">
        <span class="tag">{{ TYPE_LABELS[record.beneficiaire.type] || record.beneficiaire.type }}</span>
        <span v-if="record.domaine" class="tag">{{ record.domaine }}</span>
        <span v-if="record.beneficiaire.est_etranger" class="tag etranger">Hors France</span>
      </div>
      <div class="meta" style="margin-top:6px">
        {{ record.objet || 'Objet non précisé' }}
        <template v-if="record.financeur_nom"> · {{ record.financeur_nom }}</template>
      </div>
    </div>
    <div>
      <div class="montant num">{{ formatEurFull(record.montant) }}</div>
      <div class="meta num" style="text-align:right">{{ record.annee }}</div>
    </div>
  </div>
</template>
