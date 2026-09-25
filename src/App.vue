<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getStats } from './data/source.js'

const isSample = ref(false)
const anneeMax = ref(null)
const route = useRoute()
// La page de garde commune porte sa propre marque et son propre pied de page.
const estGarde = computed(() => route.name === 'garde')

onMounted(async () => {
  try {
    const stats = await getStats()
    isSample.value = !!stats?.meta?.is_sample
    anneeMax.value = stats?.meta?.annee_max
  } catch (e) {
    /* l'erreur est traitée dans les vues */
  }
})
</script>

<template>
  <div class="plf">
    <div class="plf-wrap">
      <header class="plf-marque">
        <span class="plf-drapeau" aria-hidden="true"><span></span><span></span><span></span></span>
        <router-link class="plf-marque-nom" to="/"><span class="plf-mot-bleu">Pour</span> <span class="plf-mot-blanc">la</span> <span class="plf-mot-rouge">France</span></router-link>
        <span class="plf-marque-devise">Indépendant · anonyme · open source</span>
      </header>
      <div class="plf-filet-tricolore" aria-hidden="true"><span></span><span></span><span></span></div>
      <nav class="plf-nav">
        <a href="#/" @click.prevent="$router.back()">← Retour</a>
        <router-link to="/">Accueil</router-link>
        <span class="plf-nav-site" aria-current="page">Subventions FR</span>
        <template v-if="!estGarde">
          <router-link to="/tableau">Tableau de bord</router-link>
          <router-link to="/liste">Rechercher</router-link>
          <router-link to="/explications">Comprendre</router-link>
          <router-link to="/methodologie">Méthodologie</router-link>
        </template>
      </nav>
    </div>

    <div v-if="isSample" class="sample-banner">
      <div class="plf-wrap">
        <strong>Données de démonstration.</strong>
        Les chiffres affichés sont fictifs et servent uniquement à illustrer le fonctionnement du site.
        Tant que cette bannière est visible, le pipeline officiel n'a pas encore alimenté la base.
      </div>
    </div>

    <main :class="{ garde: estGarde }">
      <div class="container">
        <router-view />
      </div>
    </main>

    <div class="plf-wrap">
      <footer class="plf-pied">
        <div class="plf-filet-tricolore plf-filet-tricolore--court" aria-hidden="true"><span></span><span></span><span></span></div>
        <p>Pour la France · projet citoyen indépendant · Liberté, Égalité, Fraternité</p>
        <p>
          <router-link to="/">Accueil</router-link> ·
          <a href="https://pourlafrance.github.io/Test-de-personnalite-politique/faq.html">FAQ</a> ·
          <a href="https://x.com/fracoiselibre" target="_blank" rel="noopener">Compte X</a> ·
          <a href="https://github.com/pourlafrance/subvention-FR" target="_blank" rel="noopener">Code source (GitHub)</a>
        </p>
      </footer>
    </div>
  </div>
</template>
