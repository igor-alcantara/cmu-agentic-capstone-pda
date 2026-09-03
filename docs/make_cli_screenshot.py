"""Render docs/cli_confirm_gate.png, the confirm-gate excerpt shown on presentation slide 11.

    python docs/make_cli_screenshot.py

Runs the E007 mock demo headlessly, takes the output from the Escalations block onward,
and paints it as a dark terminal image. Approval lines are drawn as they appear in an
interactive run with answers y, n, y. Needs Pillow; uses DejaVu Sans Mono from matplotlib
if present, else Consolas.
"""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "cli_confirm_gate.png"

BG, FG, BLUE, GREEN = (28, 28, 28), (220, 220, 220), (120, 180, 255), (110, 220, 170)
WRAP, SIZE, LINE_H, PAD = 100, 30, 40, 40


def _font() -> ImageFont.FreeTypeFont:
    candidates = []
    try:
        import matplotlib  # optional
        candidates.append(Path(matplotlib.__file__).parent / "mpl-data/fonts/ttf/DejaVuSansMono.ttf")
    except ImportError:
        pass
    candidates.append(Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/consola.ttf")
    for c in candidates:
        if c.exists():
            return ImageFont.truetype(str(c), SIZE)
    return ImageFont.load_default()


def _demo_output() -> str:
    cmd = [sys.executable, "-m", "pda.cli", "--employee", "E007", "--mock", "--auto-approve-none"]
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout


def _excerpt(out: str) -> list[tuple[str, tuple]]:
    lines = out.splitlines()
    start = lines.index("Escalations")
    body = lines[start:]
    # drop the plan detail between "Plan: complete" and the drafted-actions banner
    plan_i = next(i for i, l in enumerate(body) if l.startswith("Plan: complete"))
    banner_i = next(i for i, l in enumerate(body) if "drafted action(s)" in l)
    body = body[:plan_i + 1] + body[banner_i:]
    # stop after the first line of A3
    a3 = next(i for i, l in enumerate(body) if l.startswith("[A3]"))
    body = body[:a3 + 2]
    body[-1] = body[-1].rstrip() + " ..."
    answers = iter([("A1", "approved and executed:\n    " + str(ROOT / "outbox" / "E007_A1_renewal_reminder.md")),
                    ("A2", "rejected; remembered so it is not proposed the same way again")])
    styled: list[tuple[str, tuple]] = []
    for l in body:
        if l.strip() == "-> left as draft (--auto-approve-none)":
            aid, text = next(answers)
            styled.append((f"  Approve {aid}? [y/N]    -> {text}", GREEN))
        elif l.startswith(("Escalations", "Plan:")) or l.startswith("[A"):
            styled.append((l, BLUE))
        elif l.startswith("  [") and "->" in l:
            styled.append((l, GREEN))
        elif l.startswith("-----"):
            styled.append((l, FG))
        else:
            styled.append((l, FG))
    return styled


def render(styled: list[tuple[str, tuple]], out: Path) -> None:
    font = _font()
    rows: list[tuple[str, tuple]] = []
    for text, color in styled:
        for para in text.split("\n"):
            indent = len(para) - len(para.lstrip(" "))
            wrapped = textwrap.wrap(para, WRAP, subsequent_indent=" " * (indent + 2), drop_whitespace=False) or [""]
            rows.extend((w, color) for w in wrapped)
    width = int(font.getlength("M") * (WRAP + 2)) + 2 * PAD
    img = Image.new("RGBA", (width, LINE_H * len(rows) + 2 * PAD), BG + (255,))
    draw = ImageDraw.Draw(img)
    for i, (text, color) in enumerate(rows):
        draw.text((PAD, PAD + i * LINE_H), text, font=font, fill=color + (255,))
    img.save(out)
    print(f"wrote {out} ({img.width}x{img.height}, {len(rows)} lines)")


if __name__ == "__main__":
    render(_excerpt(_demo_output()), OUT)
