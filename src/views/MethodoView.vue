<script setup>
import { ref, onMounted } from 'vue'
import { getStats } from '../data/source.js'
const meta = ref(null)
onMounted(async () => { try { meta.value = (await getStats()).meta } catch (e) {} })
</script>

<template>
  <h1>Méthodologie, sources et limites</h1>
  <p class="lede">
    Ce site n'agrège que des données publiques officielles. Il assume explicitement ce qu'il ne peut pas montrer&nbsp;:
    la transparence passe autant par les chiffres que par leurs angles morts.
  </p>

  <h2>Ce que ce site ne peut pas faire (et pourquoi)</h2>
  <div class="card">
    <dl class="detail">
      <dt>Tout recenser</dt>
      <dd>Même l'État ne dispose pas d'un recensement exhaustif des aides qu'il verse. Une commission d'enquête
        du Sénat (2025) a dû produire sa propre estimation des aides aux entreprises (ordre de grandeur, 2023), faute de données consolidées. La part non documentée
        est affichée comme telle, jamais masquée.</dd>
      <dt>Relier à un impôt</dt>
      <dd>Le principe d'universalité budgétaire (non-affectation des recettes, LOLF) rend impossible de relier
        une subvention à une taxe précise&nbsp;: l'argent public est fongible. On rattache au mieux à un programme
        budgétaire. <router-link :to="{ path: '/explications', hash: '#financement' }">D'où vient l'argent&nbsp;?</router-link></dd>
      <dt>Dire qui a voté</dt>
      <dd>Le Parlement vote le budget par mission, pas subvention par subvention. Les subventions des collectivités
        relèvent de délibérations éparses. On indique l'autorité versante, pas un vote nominatif par ligne.</dd>
      <dt>Évaluer les résultats</dt>
      <dd>L'usage effectif d'une subvention n'est pas suivi en données ouvertes&nbsp;; ce champ reste donc vide.</dd>
      <dt>Nommer des personnes physiques</dt>
      <dd>Exclu par défaut&nbsp;: protection des données personnelles (arrêt CJUE du 9&nbsp;novembre 2010, C-92/09 et C-93/09, sur les aides agricoles). Seules les personnes morales apparaissent.</dd>
    </dl>
  </div>

  <h2>Classification par domaine&nbsp;: la COFOG, pas nos opinions</h2>
  <p>
    Les «&nbsp;domaines&nbsp;» (culture, écologie, social…) ne sont pas inventés. Chaque programme budgétaire est
    rattaché à une <strong>division COFOG</strong>, la classification fonctionnelle internationale (ONU/OCDE) utilisée
    par l'INSEE pour ventiler les dépenses publiques en dix fonctions. Le domaine affiché n'est qu'un alias lisible
    d'un groupe COFOG. La table de correspondance complète est publiée et contestable&nbsp;: une ligne discutable
    peut être signalée via le dépôt GitHub du projet.
  </p>

  <h2>Sources</h2>
  <ul>
    <li><strong>Associations</strong> : Données essentielles des subventions (décret n°&nbsp;2017-779 du 5&nbsp;mai 2017, schéma SCDL, conventions supérieures à 23&nbsp;000&nbsp;€)&nbsp;: 53 jeux de données publiés sur data.gouv.fr par des collectivités (nombre relevé le 25&nbsp;septembre 2026). Les montants sont ceux des <em>conventions</em> (pluriannuelles le cas échéant), datés de l'année de signature.</li>
    <li><strong>Associations (État)</strong> : «&nbsp;Jaune budgétaire&nbsp;»&nbsp;: annexe au PLF recensant les versements de l'État par bénéficiaire, avec le programme budgétaire (data.gouv.fr).</li>
    <li><strong>Agriculture</strong> : Bénéficiaires de la PAC (FEAGA/FEADER), portail de reporting public de l'ASP. Personnes morales uniquement&nbsp;: sans champ de type juridique dans le flux, seules les dénominations portant une forme juridique reconnue (GAEC, EARL, association…) sont retenues (règle volontairement conservatrice).</li>
    <li><strong>Entreprises (aides d'État)</strong> : portail Transparency Award Module de la Commission européenne (seuil de publication de 100&nbsp;000&nbsp;€ par aide selon le Sénat). <strong>Cette source n'est pas encore intégrée</strong>&nbsp;: elle ne contribue à aucune ligne à ce jour, l'export du portail n'étant pas automatisé. Un registre national des aides est prévu en France depuis le 1er janvier 2026 (Sénat, 2025).</li>
    <li><strong>Recherche (UE)</strong> : Financements Horizon Europe aux entreprises privées françaises, export CORDIS (Commission européenne). Montants&nbsp;= engagements contractualisés sur la durée du projet, rattachés à l'année de début&nbsp;: des années futures peuvent apparaître.</li>
    <li><strong>Transition écologique</strong> : Aides financières de l'ADEME (data.ademe.fr), personnes morales privées uniquement&nbsp;: les aides aux collectivités et à l'État (transferts public-public) sont écartées et comptées.</li>
    <li><strong>Enrichissement</strong> : Fiches SIRENE via l'API Recherche d'entreprises (État)&nbsp;: validation du type de bénéficiaire, activité, effectifs. Aucun montant n'en provient.</li>
    <li><strong>Classification</strong> : COFOG/CFAP (INSEE)&nbsp;; nomenclature budgétaire LOLF (Légifrance, data.gouv.fr).</li>
    <li><strong>Ordre de grandeur</strong> : rapport n°&nbsp;808 de la commission d'enquête du Sénat (2025), pour les aides aux entreprises uniquement.</li>
  </ul>

  <h2>Périmètre et choix assumés</h2>
  <div class="card">
    <dl class="detail">
      <dt>Aides d'urgence COVID</dt>
      <dd>Le fonds de solidarité (créé par l'ordonnance n°&nbsp;2020-317 du 25&nbsp;mars 2020 pour les entreprises
        touchées par la crise sanitaire) est <strong>exclu</strong>&nbsp;: dispositif exceptionnel de crise.</dd>
      <dt>Euros constants</dt>
      <dd>La série annuelle est aussi affichée en euros constants, déflatée par l'indice des prix à la
        consommation de l'INSEE (moyennes annuelles, base 2015). La table utilisée est versionnée dans le dépôt.</dd>
      <dt>L'argent qui sort sans bénéficiaire</dt>
      <dd>Une grande partie du soutien public ne passe pas par des versements nominatifs&nbsp;: les
        <strong>dépenses fiscales</strong> («&nbsp;niches&nbsp;»), des dérogations à l'impôt votées par le
        Parlement (crédits d'impôt, exonérations, taux réduits), parfaitement légales, économiquement
        équivalentes à des subventions versées «&nbsp;en creux&nbsp;», coûtent environ 90&nbsp;Md€ en 2021 (réalisation, annexe Voies et moyens du PLF&nbsp;2023), dont environ 53&nbsp;Md€ pour les
        252 dispositifs bénéficiant aux entreprises (177 chiffrés)&nbsp;: l'État en connaît le coût <em>par dispositif</em>,
        mais aucun bénéficiaire nominatif n'est publié.</dd>
      <dt>Géolocalisation</dt>
      <dd>La carte utilise le département du <em>siège</em> du bénéficiaire (codes INSEE des sources, complétés
        par SIRENE), pas le lieu d'usage de l'aide. Le taux de géolocalisation est affiché avec la carte.</dd>
      <dt>Co-financements</dt>
      <dd>Un même bénéficiaire peut apparaître dans plusieurs sources (État, UE, collectivités)&nbsp;: un
        co-financement peut alors être compté plusieurs fois. Ce recouvrement est mesuré et signalé, jamais
        déduit silencieusement.</dd>
    </dl>
  </div>

  <h2>Neutralité</h2>
  <p>
    Projet sans affiliation politique. Aucun jugement de valeur n'est porté sur l'opportunité d'une subvention&nbsp;:
    le site décrit, il ne commente pas. Le code et les données de référence sont ouverts et vérifiables.
  </p>

  <p v-if="meta" class="muted" style="font-size:.82rem;margin-top:24px">
    Données chargées&nbsp;:
    <template v-if="meta.is_sample"><strong>démonstration</strong> (fictives)</template>
    <template v-else>{{ meta.n_records }} lignes, {{ meta.annee_min }}–{{ meta.annee_max }}</template>.
  </p>
</template>
