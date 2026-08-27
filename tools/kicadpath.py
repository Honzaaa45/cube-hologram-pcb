"""Localisation de KiCad 9, sans chemin code en dur.

Ordre de recherche :
  1. variables d'environnement KICAD_SHARE / KICAD_CLI (voir .env.example)
  2. kicad-cli present dans le PATH
  3. emplacements d'installation habituels, par plateforme

Lever une erreur explicite vaut mieux qu'un plantage obscur trois appels plus
loin, donc les deux fonctions echouent avec un message qui dit quoi faire.
"""
import glob
import os
import shutil
import sys

_WIN_SHARE = [
    r"C:\Program Files\KiCad\*\share\kicad",
    r"C:\Program Files (x86)\KiCad\*\share\kicad",
]
_NIX_SHARE = [
    "/usr/share/kicad",
    "/usr/local/share/kicad",
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport",
    os.path.expanduser("~/.local/share/kicad"),
]
_WIN_CLI = [
    r"C:\Program Files\KiCad\*\bin\kicad-cli.exe",
    r"C:\Program Files (x86)\KiCad\*\bin\kicad-cli.exe",
]
_NIX_CLI = [
    "/usr/bin/kicad-cli",
    "/usr/local/bin/kicad-cli",
    "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
]


def _newest(patterns):
    """Le chemin correspondant le plus recent (tri sur la version dans le nom)."""
    found = []
    for pat in patterns:
        found.extend(glob.glob(pat) if "*" in pat else
                     ([pat] if os.path.exists(pat) else []))
    return sorted(found)[-1] if found else None


def share_dir():
    """Racine des donnees KiCad (contient symbols/ et footprints/)."""
    env = os.environ.get("KICAD_SHARE")
    if env:
        if not os.path.isdir(env):
            raise RuntimeError("KICAD_SHARE pointe sur un dossier inexistant : %s" % env)
        return env
    pats = _WIN_SHARE if sys.platform == "win32" else _NIX_SHARE
    path = _newest(pats)
    if path and os.path.isdir(os.path.join(path, "symbols")):
        return path
    raise RuntimeError(
        "Librairies KiCad introuvables. Installez KiCad 9, ou definissez "
        "KICAD_SHARE sur le dossier contenant symbols/ et footprints/ "
        "(par exemple C:\\Program Files\\KiCad\\9.0\\share\\kicad)")


def cli():
    """Chemin de l'executable kicad-cli."""
    env = os.environ.get("KICAD_CLI")
    if env:
        if not os.path.isfile(env):
            raise RuntimeError("KICAD_CLI pointe sur un fichier inexistant : %s" % env)
        return env
    found = shutil.which("kicad-cli")
    if found:
        return found
    path = _newest(_WIN_CLI if sys.platform == "win32" else _NIX_CLI)
    if path:
        return path
    raise RuntimeError(
        "kicad-cli introuvable. Ajoutez le dossier bin/ de KiCad au PATH, "
        "ou definissez KICAD_CLI sur le chemin complet de l'executable.")


if __name__ == "__main__":
    print("share : %s" % share_dir())
    print("cli   : %s" % cli())
