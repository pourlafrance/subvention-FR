// Patch de sql.js-httpvfs 0.8.x (bibliothèque non maintenue) — bug avéré :
// dans LazyUint8Array.getChunk, une lecture anticipée (speed >= 2) qui démarre
// au chunk N ne remplit que les chunks effectivement renvoyés ; si la réponse
// est courte (cas nominal de notre mode chunké : chaque fichier de chunk ne
// renvoie que lui-même, voir pipeline/split_db.py) et que le chunk demandé
// était N+1, la bibliothèque lève « doXHR failed (bug)! » au lieu de le
// récupérer. Ce patch ajoute ce repli : re-télécharger individuellement le
// chunk manquant avant d'abandonner.
//
// Lancé par `npm ci` / `npm install` (postinstall). Idempotent. Échoue
// BRUYAMMENT si le motif n'est pas trouvé (changement de version de la lib) :
// ne jamais laisser passer un build avec un worker non patché.
import { readFileSync, writeFileSync } from 'node:fs'

const FILE = new URL('../node_modules/sql.js-httpvfs/dist/sqlite.worker.js', import.meta.url)

const AVANT = 'if(void 0===this.chunks[e])throw new Error("doXHR failed (bug)!");'
const APRES =
  'if(void 0===this.chunks[e]){const r=e*this.chunkSize,n=Math.min((e+1)*this.chunkSize,this.length)-1,o=this.doXHR(r,n);' +
  'this.chunks[e]=new Uint8Array(o,0,Math.min(this.chunkSize,o.byteLength))}' +
  'if(void 0===this.chunks[e])throw new Error("doXHR failed (bug)!");'

const src = readFileSync(FILE, 'utf8')
if (src.includes(APRES)) {
  console.log('sql.js-httpvfs : worker déjà patché')
} else if (src.includes(AVANT)) {
  writeFileSync(FILE, src.replace(AVANT, APRES))
  console.log('sql.js-httpvfs : patch du repli getChunk appliqué')
} else {
  console.error('sql.js-httpvfs : motif introuvable — la version a changé, vérifier le patch !')
  process.exit(1)
}
