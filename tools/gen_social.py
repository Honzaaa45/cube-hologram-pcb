"""Fabrique docs/media/social.png (1280x640), l'apercu affiche par GitHub,
LinkedIn ou Slack quand on partage le lien du depot.

Fond sombre volontaire : la vignette apparait aussi bien sur fond clair que
sombre, un fond blanc y ferait une tache.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOARD = os.path.join(ROOT, "docs", "media", "board-top.png")
OUT = os.path.join(ROOT, "docs", "media", "social.png")

W, H = 1280, 640
BG = (11, 16, 32)
FG = (241, 245, 249)
DIM = (148, 163, 184)
ACCENT = (125, 211, 252)
VIOLET = (167, 139, 250)

FONTS = [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
FONTS_B = [r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]


def font(size, bold=False):
    for path in (FONTS_B if bold else FONTS):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # dégradé discret en haut, pour ne pas avoir un aplat mort
    for y in range(220):
        k = 1 - y / 220
        d.line([(0, y), (W, y)],
               fill=(int(BG[0] + 14 * k), int(BG[1] + 20 * k), int(BG[2] + 26 * k)))
    d.rectangle([0, 0, W - 1, 4], fill=ACCENT)

    # --- rendu de la carte, a droite ---
    if os.path.exists(BOARD):
        board = Image.open(BOARD).convert("RGBA")
        target_h = 470
        ratio = target_h / board.height
        board = board.resize((int(board.width * ratio), target_h), Image.LANCZOS)
        img.paste(board, (W - board.width - 70, (H - target_h) // 2 + 10), board)

    # --- texte, a gauche ---
    x = 78
    d.text((x, 118), "CUBE", font=font(96, True), fill=FG)
    d.text((x + 6, 232), "Afficheur holographique", font=font(34), fill=ACCENT)
    d.text((x + 6, 276), "Pepper's Ghost", font=font(34), fill=VIOLET)
    d.text((x + 6, 344), "Carte 4 couches generee par code,", font=font(23), fill=DIM)
    d.text((x + 6, 378), "verifiee par ERC, DRC et parite schema/PCB.", font=font(23), fill=DIM)

    chips = ["ESP32-S3", "AMOLED QSPI", "KiCad 9", "Python"]
    cx = x + 6
    for c in chips:
        w = d.textlength(c, font=font(20)) + 30
        d.rounded_rectangle([cx, 440, cx + w, 480], radius=20,
                            fill=(17, 28, 51), outline=(35, 54, 87))
        d.text((cx + 15, 450), c, font=font(20), fill=DIM)
        cx += w + 12

    d.text((x + 6, 528), "github.com/Honzaaa45", font=font(21), fill=(100, 116, 139))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print("ecrit %s (%dx%d, %.0f Ko)"
          % (os.path.relpath(OUT, ROOT), W, H, os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
