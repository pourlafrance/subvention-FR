<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getStats } from '../data/source.js'
import { formatEur, formatInt, formatPct, TYPE_LABELS } from '../lib/format.js'
import KpiCard from '../components/KpiCard.vue'
import DomainChart from '../components/DomainChart.vue'
import TimeSeriesChart from '../components/TimeSeriesChart.vue'
import FranceMap from '../components/FranceMap.vue'
import LoadingState from '../components/LoadingState.vue'

const router = useRouter()
const stats = ref(null)
const error = ref(null)
const q = ref('')

// Année de référence des agrégats « dernière année » : la plus récente non
// future (les engagements pluriannuels créent des années futures légitimes).
const anneeRef = (s) => s?.meta?.annee_ref || s?.meta?.annee_max
const lastYearVolume = (s) => {
  const arr = s?.kpi?.volume_total_annuel || []
  const entry = arr.find((e) => e.annee === anneeRef(s))
  return entry ? entry.montant : (arr.length ? arr[arr.length - 1].montant : null)
}

onMounted(async () => {
  try {
    stats.value = await getStats()
  } catch (e) {
    error.value = "Impossible de charger les données. Le pipeline n'a peut-être pas encore tourné."
  }
})

function go(query) {
  router.push({ name: 'liste', query })
}
function runSearch() {
  router.push({ name: 'liste', query: q.value ? { q: q.value } : {} })
}
</script>

<template>
  <div v-if="error" class="empty">{{ error }}</div>

  <template v-else-if="stats">
    <h1>Où va l'argent public&nbsp;?</h1>
    <p class="lede">
      Cartographie des subventions versées par l'État et l'Union européenne aux associations, entreprises
      et exploitations, à partir des seules données publiques officielles.
    </p>

    <!-- Hero honnête : part documentée -->
    <div class="card" style="margin-top:22px">
      <div class="label muted" style="font-size:.85rem">Part des subventions effectivement documentée dans des données ouvertes</div>
      <div class="value num" style="font-size:2.4rem;font-weight:700;letter-spacing:-.02em;color:var(--bleu)">
        {{ formatPct(stats.kpi.estimation.part_visible) }}
      </div>
      <div style="margin-top:4px;max-width:65ch">
        <strong class="num">{{ formatEur(stats.kpi.estimation.volume_visible_eur) }}</strong> retracés
        ligne à ligne sur ce site, rapportés aux
        <strong class="num">~{{ formatEur(stats.kpi.estimation.volume_estime_total_eur) }}</strong> d'aides
        annuelles estimées par la commission d'enquête du Sénat (2025).
      </div>
      <p class="muted" style="max-width:65ch;margin:10px 0 0">
        Ce total n'est qu'une estimation, car il n'existe aucune comptabilité exhaustive des aides
        publiques&nbsp;— même l'État ne sait pas retracer le reste.
        <template v-if="stats.kpi.estimation.depenses_fiscales">
          À elles seules, les niches fiscales aux entreprises pèsent
          <strong class="num">{{ formatEur(stats.kpi.estimation.depenses_fiscales.total_entreprises_eur) }}</strong>
          par an&nbsp;: coût connu, bénéficiaires jamais publiés.
        </template>
      </p>
      <p style="margin:10px 0 0;font-size:.9rem">
        <router-link :to="{ path: '/explications', hash: '#niche-fiscale' }">Qu'appelle-t-on une niche fiscale&nbsp;?</router-link>
        &nbsp;·&nbsp;
        <router-link :to="{ path: '/explications', hash: '#total-inconnu' }">Pourquoi le total est-il inconnu&nbsp;?</router-link>
        &nbsp;·&nbsp;
        <router-link to="/methodologie">Notre méthode</router-link>
      </p>
    </div>

    <!-- Recherche rapide -->
    <div class="search" style="margin-top:22px">
      <input type="text" v-model="q" placeholder="Rechercher un bénéficiaire (association, entreprise…)"
             @keyup.enter="runSearch" aria-label="Rechercher un bénéficiaire" />
      <button class="btn" @click="runSearch">Rechercher</button>
    </div>

    <!-- KPI cliquables -->
    <div class="kpi-grid">
      <KpiCard label="Associations subventionnées"
               :value="formatInt(stats.kpi.associations.count)"
               :sub="formatEur(stats.kpi.associations.volume_eur) + ' au total'"
               cta="Voir les associations"
               @activate="go({ type: 'association' })" />
      <KpiCard label="Entreprises subventionnées"
               :value="formatInt(stats.kpi.entreprises.count)"
               :sub="formatEur(stats.kpi.entreprises.volume_eur) + ' au total'"
               cta="Voir les entreprises"
               @activate="go({ type: 'entreprise' })" />
      <KpiCard label="Volume annuel (dernière année)"
               :value="formatEur(lastYearVolume(stats))"
               :sub="'Année ' + (anneeRef(stats) || '')"
               cta="Voir toutes les subventions"
               @activate="go({})" />
      <KpiCard label="Versé hors France"
               :value="formatEur(stats.kpi.etranger.volume_eur)"
               :sub="formatPct(stats.kpi.etranger.share) + ' du total'"
               cta="Voir les bénéficiaires hors France"
               @activate="go({ etranger: '1' })" />
    </div>

    <h2>Répartition par domaine</h2>
    <p class="muted" style="margin-top:-6px">Ensemble de la période documentée. Domaines dérivés de la classification COFOG.</p>
    <DomainChart :domaines="stats.domaines" @select="(d) => go({ domaine: d })" />

    <template v-if="stats.departements && stats.departements.liste.length">
      <h2>Répartition territoriale</h2>
      <p class="muted" style="margin-top:-6px">
        Volume documenté par département du siège du bénéficiaire, toute période confondue.
      </p>
      <FranceMap :data="stats.departements" />
    </template>

    <h2>Évolution du volume annuel, par source</h2>
    <p class="muted" style="margin-top:-6px">
      Les variations reflètent d'abord l'élargissement progressif des données publiées
      (chaque source ne couvre que certains exercices), pas seulement l'effort public réel.
    </p>
    <TimeSeriesChart :serie="stats.kpi.volume_total_annuel"
                     :par-source="stats.kpi.volume_par_source || []"
                     @select="(a) => go({ annee: String(a) })" />

    <template v-if="stats.top_beneficiaires && stats.top_beneficiaires.length">
      <h2>Principaux bénéficiaires</h2>
      <p class="muted" style="margin-top:-6px">
        Cumul sur l'ensemble de la période documentée. Personnes morales uniquement.
      </p>
      <div class="rows">
        <div class="row" v-for="(b, i) in stats.top_beneficiaires" :key="b.id">
          <div>
            <router-link class="nom" :to="`/beneficiaire/${encodeURIComponent(b.id)}`">
              {{ i + 1 }}. {{ b.nom }}
            </router-link>
            <div class="meta" style="margin-top:4px">
              <span class="tag">{{ TYPE_LABELS[b.type] || b.type }}</span>
            </div>
          </div>
          <div>
            <div class="montant num">{{ formatEur(b.total_eur) }}</div>
            <div class="meta num" style="text-align:right">{{ b.n }} subvention<template v-if="b.n > 1">s</template></div>
          </div>
        </div>
      </div>
    </template>
  </template>

  <LoadingState v-else />
</template>
