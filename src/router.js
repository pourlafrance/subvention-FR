import { createRouter, createWebHashHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'

// Routage par hash : pas de 404 au rafraîchissement sur GitHub Pages,
// et fonctionne quel que soit le nom du dépôt.
const routes = [
  { path: '/', name: 'home', component: HomeView },
  { path: '/liste', name: 'liste', component: () => import('./views/ListView.vue') },
  { path: '/beneficiaire/:id', name: 'beneficiaire', component: () => import('./views/BeneficiaireView.vue') },
  { path: '/methodologie', name: 'methodo', component: () => import('./views/MethodoView.vue') },
  { path: '/explications', name: 'explications', component: () => import('./views/ExplicationsView.vue') },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior(to) {
    if (to.hash) return { el: to.hash, top: 12 }
    return { top: 0 }
  },
})
