<script setup>
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getBeneficiaire } from '../data/source.js'
import { formatEurFull, formatEur, TYPE_LABELS } from '../lib/format.js'
import SubventionRow from '../components/SubventionRow.vue'
import YearSparkline from '../components/YearSparkline.vue'

const route = useRoute()
const data = ref(null)
const loading = ref(true)

async function load() {
  loading.value = true
  data.value = await getBeneficiaire(decodeURIComponent(route.params.id))
  loading.value = false
}
onMounted(load)
watch(() => route.params.id, load)
</script>

<template>
  <div v-if="loading" class="empty">Chargement…</div>
  <div v-else-if="!data" class="empty">Bénéficiaire introuvable.</div>

  <template v-else>
    <router-link to="/liste" class="muted">← Retour à la recherche</router-link>
    <h1 style="margin-top:10px">{{ data.beneficiaire.nom }}</h1>
    <div class="meta" style="margin-bottom:18px">
      <span class="tag">{{ TYPE_LABELS[data.beneficiaire.type] || data.beneficiaire.type }}</span>
      <span v-if="data.beneficiaire.est_etranger" class="tag etranger">Hors France ({{ data.beneficiaire.pays }})</span>
    </div>

    <div class="card">
      <dl class="detail">
        <dt>Total reçu</dt>
        <dd class="num"><strong>{{ formatEurFull(data.total) }}</strong> sur {{ data.n }} subvention<span v-if="data.n>1">s</span></dd>
        <dt>Aidé depuis</dt>
        <dd class="num">{{ data.premiere_annee }}</dd>
        <dt v-if="data.beneficiaire.siren">SIREN</dt>
        <dd v-if="data.beneficiaire.siren" class="num">{{ data.beneficiaire.siren }}</dd>
        <dt v-if="data.beneficiaire.commune">Commune</dt>
        <dd v-if="data.beneficiaire.commune">{{ data.beneficiaire.commune }}</dd>
        <dt v-if="data.beneficiaire.activite">Activité</dt>
        <dd v-if="data.beneficiaire.activite">{{ data.beneficiaire.activite }}</dd>
        <dt v-if="data.beneficiaire.effectifs">Effectifs</dt>
        <dd v-if="data.beneficiaire.effectifs">{{ data.beneficiaire.effectifs }} <span class="muted">(SIRENE)</span></dd>
      </dl>
      <YearSparkline :subventions="data.subventions" style="margin-top:14px" />
    </div>

    <h2>Détail des subventions</h2>
    <div class="rows">
      <SubventionRow v-for="s in data.subventions" :key="s.id" :record="s" />
    </div>
    <p class="muted" style="font-size:.82rem;margin-top:14px">
      Sources des lignes ci-dessus : {{ [...new Set(data.subventions.map(s => s.source))].join(', ') }}.
    </p>
  </template>
</template>
