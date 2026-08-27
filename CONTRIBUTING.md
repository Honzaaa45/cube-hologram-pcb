# Contribuer

Merci de l'intérêt. Ce projet est une carte électronique dont **toute la CAO est
générée par du code**. La règle qui découle de ça tient en une phrase :

> On ne modifie jamais `hw/*.kicad_sch` ni `hw/*.kicad_pcb` à la main dans une
> contribution. On modifie `tools/design.py`, puis on régénère.

Une modification faite directement dans KiCad serait écrasée à la prochaine
génération. Les seules exceptions sont le routage manuel de finition (voir plus
bas) et l'exploration : ouvrir le projet dans KiCad pour regarder, toujours.

## Mettre en place

Il faut Python 3.9+ et **KiCad 9** installé (les scripts lisent ses
bibliothèques officielles de symboles et d'empreintes).

```bash
git clone https://github.com/Honzaaa45/cube-hologram-pcb.git
```

```bash
cd cube-hologram-pcb && python tools/validate.py
```

Si KiCad n'est pas trouvé automatiquement, renseignez `KICAD_SHARE` et
`KICAD_CLI` (voir `.env.example`).

## Le cycle de travail

1. Modifier `tools/design.py` — composants, netlist, ou placement.
2. Régénérer :

```bash
python tools/gen_project.py && python tools/gen_sch.py && python tools/gen_pcb.py
```

3. Si le placement a bougé, relancer le solveur puis le routeur :

```bash
python tools/place.py && python tools/router.py && python tools/gen_pcb.py
```

4. Remplir les plans de cuivre — indispensable, sinon le DRC signale à tort
   toutes les pastilles de masse comme non connectées :

```bash
"C:\Program Files\KiCad\9.0\bin\python.exe" tools/fill_zones.py
```

5. Vérifier avant de proposer :

```bash
python tools/validate.py && python tools/check_cad.py
```

Ces deux commandes sont exactement ce que lance la CI. Si elles passent chez
vous, elles passeront sur GitHub.

## Ce qui est attendu d'une contribution

- `validate.py` et `check_cad.py` au vert. `check_cad.py` compare aux seuils
  de l'état vérifié : améliorer est permis, régresser bloque.
- Les fichiers générés (`hw/cube.kicad_*`) sont commités **avec** la
  modification de `design.py` qui les produit. Ils font partie du livrable.
- Messages de commit en français, préfixés `feat:`, `fix:`, `docs:`, `chore:`
  ou `refactor:`.
- Pas de reformatage massif dans un commit qui change autre chose.

## Le cas du routage manuel

Quatre liaisons restent à router à la main (listées dans `docs/CARTE.md`).
Elles vivent dans `hw/cube.kicad_pcb` et **seraient perdues** si vous relancez
`gen_pcb.py`. Deux options si vous y touchez :

- soit vous les tracez dans Pcbnew et vous ne régénérez plus le PCB ;
- soit vous améliorez `tools/router.py` pour qu'il les trouve — c'est la
  contribution qui a le plus de valeur ici, et il y a de la marge : le routeur
  actuel ne fait pas de rip-up local, seulement un réordonnancement global.

## Signaler un problème

Une issue utile contient : ce que vous attendiez, ce qui s'est passé, la sortie
complète de la commande, votre OS et `kicad-cli --version`. S'il s'agit d'une
erreur de conception électronique, indiquez la référence du composant et la
page de datasheet — c'est ce qui permet de trancher vite.
