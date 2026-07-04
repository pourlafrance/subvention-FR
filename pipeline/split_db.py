"""Découpe subventions.db en fichiers de chunks pour GitHub Pages.

POURQUOI : la CDN de GitHub Pages sert les requêtes Range dans l'espace des
octets COMPRESSÉS (constaté 2026-07 : `Content-Range .../<taille gzip>` et
corps = tranche du flux gzip). Un navigateur envoyant toujours
`Accept-Encoding: gzip`, les Range partiels de sql.js-httpvfs sont
inexploitables (« database disk image is malformed »). En revanche une plage
couvrant TOUT le fichier renvoie le flux gzip complet, que le navigateur
décompresse correctement.

La parade : découper la base en fichiers de CHUNK octets et régler
`requestChunkSize == serverChunkSize == CHUNK` côté front — chaque requête
couvre alors exactement un fichier entier. Voir src/data/sqlite.adapter.md.

    python3 -m pipeline.split_db public/data/subventions.db

Écrit <dossier>/db/subventions.db.0000, .0001… (CHUNK et SUFFIXE doivent
rester alignés avec src/data/source.sqlite.js).
"""
from __future__ import annotations

import os
import sys

CHUNK = 1024 * 1024  # 1 Mio
SUFFIXE = 4          # subventions.db.0000 … (jusqu'à ~10 Go de base)


def split(db_path: str) -> dict:
    out_dir = os.path.join(os.path.dirname(db_path), "db")
    os.makedirs(out_dir, exist_ok=True)
    # purge des chunks d'un run précédent (la base peut rétrécir)
    for f in os.listdir(out_dir):
        if f.startswith("subventions.db."):
            os.remove(os.path.join(out_dir, f))
    n = 0
    with open(db_path, "rb") as src:
        while True:
            bloc = src.read(CHUNK)
            if not bloc:
                break
            with open(os.path.join(out_dir, f"subventions.db.{n:0{SUFFIXE}d}"), "wb") as out:
                out.write(bloc)
            n += 1
    return {"chunks": n, "chunk_bytes": CHUNK, "dir": out_dir}


if __name__ == "__main__":
    info = split(sys.argv[1])
    print(f"{info['chunks']} chunks de {info['chunk_bytes']} octets dans {info['dir']}")
