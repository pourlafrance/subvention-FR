import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Base relative : fonctionne quel que soit le nom du dépôt sur GitHub Pages,
// à condition d'utiliser le routage par hash (voir src/router.js).
export default defineConfig({
  plugins: [vue()],
  base: './',
  build: {
    outDir: 'dist',
    // Les fichiers de données restent dans public/ et sont copiés tels quels.
    assetsInlineLimit: 0
  }
})
