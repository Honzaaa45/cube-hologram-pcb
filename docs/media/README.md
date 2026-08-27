# Ressources visuelles

| Fichier | Origine | Régénération |
|---|---|---|
| `banner-light.svg` / `banner-dark.svg` | Bannière animée (SMIL), écrite à la main. Schéma optique Pepper's Ghost : dalle, cube séparateur, lame à 45°, rayons, image virtuelle. | manuelle |
| `board-top.png` / `board-bottom.png` | Rendus 3D KiCad, **fond transparent** pour rester lisibles sur les deux thèmes GitHub. | `python tools/gen_fab.py` |
| `social.png` | Aperçu social 1280 × 640 (GitHub, LinkedIn, Slack). | `python tools/gen_social.py` |
| `demo.gif` | **Manquant.** Réservé à la démonstration du prototype physique. | à filmer — voir ci-dessous |

## Ce qu'il faut filmer pour `demo.gif`

La carte n'est pas encore fabriquée : cette démonstration ne peut pas exister aujourd'hui.
Quand le prototype fonctionnera, capturer une boucle de **6 à 10 secondes**, en **800 × 600** ou moins,
sous **8 Mo** (limite d'affichage confortable sur GitHub) :

1. **Plan large, 2 s** — l'objet posé sur un bureau, boîtier fermé, dans une pièce peu éclairée.
   C'est l'obscurité relative qui rend l'illusion crédible.
2. **Plan serré sur le cube, 4 s** — l'animation qui flotte à l'intérieur. Filmer légèrement de côté
   puis se déplacer : c'est le déplacement du point de vue qui prouve que l'image flotte réellement,
   une vue fixe pourrait passer pour un autocollant.
3. **Fin, 2 s** — la main qui s'approche pour déclencher le capteur de distance, si cette fonction est
   implémentée dans le firmware.

Contraintes de prise de vue : trépied obligatoire (l'illusion supporte mal le tremblement), pas de
lumière directe sur la face avant du cube, et **ne pas filmer en contre-jour** — le halo parasite
détruirait le noir dont dépend tout l'effet.

Conversion depuis une vidéo :

```bash
ffmpeg -i demo.mp4 -vf "fps=15,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" -loop 0 docs/media/demo.gif
```
