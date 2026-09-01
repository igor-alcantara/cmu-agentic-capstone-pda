"""Regenerate the two architecture figures with matplotlib (not a runtime dependency).

    pip install matplotlib
    python docs/make_figures.py
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

HERE = Path(__file__).resolve().parent
BLUE, DARK, AGENT, PANEL = "#2E74B5", "#1F3864", "#EAF1F8", "#BFD3E6"
CODE_FILL, CODE_EDGE = "#F2F2F2", "#9AA7B4"
STATE_FILL, STATE_EDGE = "#FFF6E0", "#D9A93B"
GATE_FILL, GATE_EDGE = "#E9F3EA", "#4E8A57"


def box(ax, x, y, w, h, text, fill=AGENT, edge=BLUE, size=8.5, bold=False, style="round,pad=0.3,rounding_size=1.2"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=style, linewidth=1.2, edgecolor=edge, facecolor=fill))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color=DARK,
            fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, p, q, dashed=False, rad=0.0, color=DARK):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=11, linewidth=1.1, color=color,
                                 linestyle="--" if dashed else "-", connectionstyle=f"arc3,rad={rad}"))


def figure1(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=200)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 52)
    ax.axis("off")
    # phase panels
    for x, w, label in [(2, 30, "A. Gather"), (34, 14, "B. Freeze"), (50, 30, "C. Synthesize"), (82, 16, "D. Act")]:
        ax.add_patch(FancyBboxPatch((x, 3), w, 44, boxstyle="round,pad=0.2,rounding_size=1", linewidth=1,
                                    edgecolor=PANEL, facecolor="white"))
        ax.text(x + w / 2, 45, label, ha="center", va="center", fontsize=9, color=BLUE, fontweight="bold")
    # orchestrator across the top
    box(ax, 2, 49, 96, 0.01, "", fill="white", edge="white")
    ax.text(50, 50.5, "Orchestrator: ReAct loop, memory, drafting tools, confirm gate. Sole writer of the packet.",
            ha="center", va="center", fontsize=8.5, color=DARK, fontweight="bold")
    # phase A agents
    box(ax, 4, 32, 12, 8, "Profile\nAnalyst")
    box(ax, 18, 32, 12, 8, "Context\nResearcher")
    box(ax, 11, 18, 12, 8, "Resource\nScout")
    box(ax, 4, 6, 12, 7, "SQLite\nrow-scoped", fill=CODE_FILL, edge=CODE_EDGE, size=7.5)
    box(ax, 18, 6, 12, 7, "Role-doc index\n3.1 safeguards", fill=CODE_FILL, edge=CODE_EDGE, size=7.5)
    arrow(ax, (10, 13), (10, 32))
    arrow(ax, (24, 13), (24, 32))
    arrow(ax, (10, 32), (14, 26))
    ax.text(15, 30, "gap list", fontsize=7, color=DARK)
    box(ax, 4, 18, 6, 6, "allowlist\nqueries\nverifier", fill=CODE_FILL, edge=CODE_EDGE, size=6.3)
    arrow(ax, (10, 21), (11, 21))
    # phase B state store
    box(ax, 36, 22, 10, 12, "Shared\nstate store\n\nfrozen\npacket\n(typed)", fill=STATE_FILL, edge=STATE_EDGE, size=7.5)
    box(ax, 36, 8, 10, 7, "relevance\ncheck +\nfreeze()", fill=CODE_FILL, edge=CODE_EDGE, size=7)
    arrow(ax, (41, 15), (41, 22))
    arrow(ax, (30, 36), (36, 30))
    arrow(ax, (23, 22), (36, 27))
    # phase C
    box(ax, 52, 30, 12, 8, "Planner\n(proposes)")
    box(ax, 66, 30, 12, 8, "Critic\n(ranks siblings)")
    box(ax, 52, 12, 26, 9, "Deterministic hard checks\nevery gap, verified resources only,\nhours within limit, dates valid",
        fill=CODE_FILL, edge=CODE_EDGE, size=7)
    arrow(ax, (46, 28), (52, 34))
    arrow(ax, (58, 30), (60, 21))
    arrow(ax, (70, 21), (72, 30))
    arrow(ax, (64, 36), (66, 36), dashed=True, rad=-0.4)
    ax.text(65, 41.5, "bounded two-way\nper depth", ha="center", fontsize=6.5, color=DARK)
    ax.text(65, 9, "beam 2 / branch 3 / depth 3", ha="center", fontsize=7, color=DARK)
    # phase D
    box(ax, 84, 28, 12, 9, "Drafts\nslots filled\nby code", fill=CODE_FILL, edge=CODE_EDGE, size=7)
    box(ax, 84, 10, 12, 10, "Human\nconfirm gate\napproval token", fill=GATE_FILL, edge=GATE_EDGE, size=7, bold=True)
    arrow(ax, (78, 34), (84, 33))
    arrow(ax, (90, 28), (90, 20))
    ax.text(90, 6, "outbox", ha="center", fontsize=7, color=DARK)
    arrow(ax, (90, 10), (90, 7.5))
    # gathering retry
    arrow(ax, (36, 30), (30, 40), dashed=True, rad=0.3)
    ax.text(30, 43, "capped retry", fontsize=6.5, color=DARK, ha="center")
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def figure2(path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5), dpi=200)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 50)
    ax.axis("off")
    ax.text(50, 47.5, "Tree of Thought over the frozen packet: rules bound the set, the Critic orders it",
            ha="center", fontsize=9.5, color=BLUE, fontweight="bold")
    # depth labels
    for y, label in [(38, "depth 1: outline"), (24, "depth 2: skeleton"), (10, "depth 3: full plan")]:
        ax.text(3, y + 3, label, fontsize=7.5, color=DARK, va="center")
    root = (50, 44)
    d1 = [(30, 36), (50, 36), (70, 36)]
    for i, (x, y) in enumerate(d1):
        rej = i == 2
        box(ax, x - 6, y, 12, 6, "outline C\nmisses a gap" if rej else f"outline {'AB'[i]}",
            fill="#FBE9E7" if rej else AGENT, edge="#C0504D" if rej else BLUE, size=7)
        arrow(ax, root, (x, y + 6))
    ax.text(50, 45, "Planner proposes 3", ha="center", fontsize=7, color=DARK)
    # gate 1
    ax.add_patch(FancyBboxPatch((12, 31), 76, 3.2, boxstyle="round,pad=0.1", linewidth=1, edgecolor=CODE_EDGE, facecolor=CODE_FILL))
    ax.text(50, 32.6, "hard checks (code)  ->  Critic ranks survivors  ->  keep 2", ha="center", fontsize=7, color=DARK)
    d2 = [(20, 22), (32, 22), (44, 22), (56, 22), (68, 22), (80, 22)]
    parents = [(30, 36), (30, 36), (30, 36), (50, 36), (50, 36), (50, 36)]
    for i, ((x, y), (px, py)) in enumerate(zip(d2, parents)):
        rej = i in (2, 5)
        label = ("A3\nover hours" if i == 2 else "B3\nover hours") if rej else f"{'AAABBB'[i]}{i % 3 + 1}"
        box(ax, x - 5, y, 10, 6, label, fill="#FBE9E7" if rej else AGENT, edge="#C0504D" if rej else BLUE, size=6.5)
        arrow(ax, (px, py), (x, y + 6), color="#9AA7B4")
    ax.add_patch(FancyBboxPatch((12, 17), 76, 3.2, boxstyle="round,pad=0.1", linewidth=1, edgecolor=CODE_EDGE, facecolor=CODE_FILL))
    ax.text(50, 18.6, "hard checks (code)  ->  Critic ranks survivors  ->  keep 2", ha="center", fontsize=7, color=DARK)
    d3 = [(26, 8), (38, 8), (50, 8), (62, 8), (74, 8), (86, 8)]
    parents3 = [(20, 22), (20, 22), (20, 22), (32, 22), (32, 22), (32, 22)]
    for i, ((x, y), (px, py)) in enumerate(zip(d3, parents3)):
        rej = i in (2, 5)
        label = "cites R999\nunverified" if rej else f"plan {'AAABBB'[i]}{i % 3 + 1}"
        win = i in (0, 1)
        box(ax, x - 5, y, 10, 6, label, fill="#FBE9E7" if rej else (GATE_FILL if win else AGENT),
            edge="#C0504D" if rej else (GATE_EDGE if win else BLUE), size=6.5, bold=win)
        arrow(ax, (px, py), (x, y + 6), color="#9AA7B4")
    ax.text(50, 3, "final ranking: winner and runner-up; the Critic's categorical 'close call' shows both to the employee",
            ha="center", fontsize=7, color=DARK)
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    figure1(HERE / "figure1_architecture.png")
    figure2(HERE / "figure2_tot.png")
    print("figures written to", HERE)
