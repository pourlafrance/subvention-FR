<script setup>
// Page de garde commune « Pour la France » : même gabarit sur les trois sites,
// seule la carte du site courant est mise en avant (charte commune).
</script>

<template>
  <div class="garde">

    <section class="plf-garde-hero">
      <span class="plf-kicker">Observatoire citoyen</span>
      <h1>Subventions FR</h1>
      <p>Où va l'argent public&nbsp;? Les subventions publiques françaises à partir des données officielles, sourcées et sans commentaire.</p>
      <div class="plf-garde-actions">
        <router-link class="plf-btn" to="/tableau">Explorer les subventions</router-link>
        <a class="plf-btn-2" href="https://pourlafrance.github.io/Test-de-personnalite-politique/faq.html#subventions">Méthode et sources</a>
      </div>
    </section>

    <section class="plf-garde-outils" aria-label="Les trois outils">
      <span class="plf-kicker">Les trois outils</span>
      <div class="plf-cartes">

        <article class="plf-carte">
          <div class="plf-carte-tete"><span class="plf-carre"></span></div>
          <h3>Test de personnalité politique</h3>
          <p>Comparez vos opinions aux programmes des candidats à l'élection présidentielle. Indépendant, anonyme, open source.</p>
          <a class="plf-carte-btn" href="https://pourlafrance.github.io/Test-de-personnalite-politique/">Commencer le test</a>
        </article>

        <article class="plf-carte">
          <div class="plf-carte-tete"><span class="plf-carre"></span></div>
          <h3>Qu'auriez-vous voté&nbsp;?</h3>
          <p>Pour chaque texte voté à l'Assemblée nationale, donnez votre avis puis découvrez ce qu'ont voté les groupes politiques.</p>
          <a class="plf-carte-btn" href="https://pourlafrance.github.io/Votre-vote/">Ouvrir les scrutins</a>
        </article>

        <article class="plf-carte plf-carte--ici">
          <div class="plf-carte-tete">
            <span class="plf-carre"></span>
            <span class="plf-ici-label">Vous êtes ici</span>
          </div>
          <h3>Subventions FR</h3>
          <p>Où va l'argent public&nbsp;? Les subventions publiques françaises à partir des données officielles, sourcées et sans commentaire.</p>
          <router-link class="plf-carte-btn" to="/tableau">Explorer les données</router-link>
        </article>

      </div>

      <div class="plf-filet-tricolore plf-filet-tricolore--court" aria-hidden="true"><span></span><span></span><span></span></div>
      <p class="plf-garde-methode" id="methode">Aucune donnée collectée. Vos réponses restent sur votre appareil. Données publiques&nbsp;: open data de l'Assemblée nationale, programmes officiels des candidats, annuaire des subventions de l'État.</p>
    </section>
  </div>
</template>

<style scoped>
.garde { display: flex; flex-direction: column; }
.plf-garde-outils { padding-bottom: 8px; }
</style>
