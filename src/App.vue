<script setup>
import { ref, onMounted } from 'vue'
import { getStats } from './data/source.js'

const isSample = ref(false)
const anneeMax = ref(null)

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
  <div class="tricolore" aria-hidden="true"><i></i><i></i><i></i></div>

  <header class="site">
    <div class="container bar">
      <router-link to="/" class="brand">
        Subventions FR
        <small>Où va l'argent public ? — données officielles, sourcées</small>
      </router-link>
      <nav>
        <router-link to="/">Accueil</router-link>
        <router-link to="/liste">Rechercher</router-link>
        <router-link to="/explications">Comprendre</router-link>
        <router-link to="/methodologie">Méthodologie</router-link>
      </nav>
    </div>
  </header>

  <div v-if="isSample" class="sample-banner">
    <div class="container">
      <strong>Données de démonstration.</strong>
      Les chiffres affichés sont fictifs et servent uniquement à illustrer le fonctionnement du site.
      Tant que cette bannière est visible, le pipeline officiel n'a pas encore alimenté la base.
    </div>
  </div>

  <main>
    <div class="container">
      <router-view />
    </div>
  </main>

  <footer class="site">
    <div class="container">
      <p>
        Projet citoyen, politiquement neutre. Données issues exclusivement de sources publiques officielles
        (data.gouv.fr, INSEE, ASP, Commission européenne). Voir la
        <router-link to="/methodologie">méthodologie et les limites</router-link>.
      </p>
      <p class="muted">Aucune donnée nominative de personne physique. Classification par fonction COFOG (INSEE).</p>
    </div>
  </footer>
</template>
