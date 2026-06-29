"""Generate the graphical (visual) abstract for the GCR resilience map paper.

The figure is built around a three-circle Venn diagram of the paper's three
global-catastrophe families and answers a single question: *what makes a
country resilient to each type of catastrophe, and where do those resilience
factors overlap?*

* Each circle is one catastrophe family
  (sunlight reduction, infrastructure loss, biological); the family name sits
  outside its circle.
* Text inside the single-set regions names the resilience factor that helps
  against that family alone.
* The pairwise lenses name a factor that helps against two families at once.
* The central region names the cross-cutting factors that help against *all*
  three families.
* The takeaway strip highlights Australia & New Zealand: they fare best across
  scenarios, yet stay vulnerable — especially without global cooperation and
  trade.
"""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyBboxPatch

# ---------------------------------------------------------------------------
# Paths and style
# ---------------------------------------------------------------------------
project_root = Path(__file__).parent.parent
output_path = project_root / "results" / "figures"
output_path.mkdir(parents=True, exist_ok=True)

try:
    plt.style.use(
        "https://raw.githubusercontent.com/allfed/"
        "ALLFED-matplotlib-style-sheet/main/ALLFED.mplstyle"
    )
except Exception:
    pass

# ---------------------------------------------------------------------------
# Palette — one hue per catastrophe family
# ---------------------------------------------------------------------------
INK = "#222222"
GREY = "#5f5f5f"

SUN = "#e3922b"  # ASRS  — sunlight reduction (amber)
SUN_DK = "#a55f0c"
INFRA = "#3f7fc4"  # GCIL  — infrastructure loss (blue)
INFRA_DK = "#205089"
BIO = "#9152a8"  # GCBR  — biological (purple)
BIO_DK = "#5f2f74"

SAFE_DK = "#1f5d22"      # Australia / New Zealand accent
FOOT_BG = "#f0f0f0"      # takeaway strip background (muted neutral)

# ---------------------------------------------------------------------------
# Figure — square so the Venn circles stay circular (graphical abstract)
# ---------------------------------------------------------------------------
MM = 1 / 25.4
SIDE = 95 * MM
fig = plt.figure(figsize=(SIDE, SIDE))
fig.patch.set_facecolor("white")

ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_aspect("equal")
ax.axis("off")


def chip(x, y, w, h, facecolor, edgecolor="none", lw=0):
    """Rounded rectangle in axis coordinates."""
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0,rounding_size={0.4 * h}",
        mutation_aspect=1,
        facecolor=facecolor,
        edgecolor=edgecolor,
        linewidth=lw,
        transform=ax.transData,
        clip_on=False,
    )
    ax.add_patch(patch)
    return patch


def lines(
    x,
    y,
    rows,
    fontsize,
    color=INK,
    weight="normal",
    ha="center",
    line_h=0.027,
    style="normal",
):
    """Draw pre-split lines top-down, centred vertically on the block."""
    top = y + (len(rows) - 1) * line_h / 2
    for i, row in enumerate(rows):
        ax.text(
            x,
            top - i * line_h,
            row,
            ha=ha,
            va="center",
            fontsize=fontsize,
            color=color,
            fontweight=weight,
            fontstyle=style,
            linespacing=1.0,
        )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
ax.text(
    0.5, 0.975,
    "Literature review",
    ha="center", va="center", fontsize=5.2, fontweight="normal", color=GREY,
)
ax.text(
    0.5,
    0.945,
    "What factors make countries more resilient",
    ha="center",
    va="center",
    fontsize=6.3,
    fontweight="bold",
    color=INK,
)
ax.text(
    0.5,
    0.913,
    "to different kinds of global catastrophes?",
    ha="center",
    va="center",
    fontsize=6.3,
    fontweight="bold",
    color=INK,
)

# ---------------------------------------------------------------------------
# Venn geometry (equal aspect → true circles)
# ---------------------------------------------------------------------------
cx, cy = 0.5, 0.450
R = 0.245
D = 0.145

T = (cx, cy + D)  # ASRS   (top)
LL = (cx - D * 0.866, cy - D * 0.5)  # GCIL   (lower-left)
LR = (cx + D * 0.866, cy - D * 0.5)  # GCBR   (lower-right)

for (ccx, ccy), face, edge in [
    (T, SUN, SUN_DK),
    (LL, INFRA, INFRA_DK),
    (LR, BIO, BIO_DK),
]:
    ax.add_patch(Circle((ccx, ccy), R, facecolor=face, alpha=0.20,
                         edgecolor="none", zorder=1))
    ax.add_patch(Circle((ccx, ccy), R, facecolor="none",
                         edgecolor=edge, linewidth=1.0, zorder=4))

# ---------------------------------------------------------------------------
# Family names + example triggers — placed OUTSIDE each circle
# ---------------------------------------------------------------------------
# Top circle
ax.text(
    0.5,
    0.876,
    "SUNLIGHT REDUCTION",
    ha="center",
    va="center",
    fontsize=5.6,
    fontweight="bold",
    color=SUN_DK,
)
ax.text(
    0.5,
    0.852,
    "nuclear · volcanic · impact winters",
    ha="center",
    va="center",
    fontsize=4.1,
    fontstyle="italic",
    color=GREY,
)

# Lower-left circle
lines(
    0.095,
    0.180,
    ["INFRASTRUCTURE", "LOSS"],
    fontsize=5.0,
    color=INFRA_DK,
    weight="bold",
    line_h=0.027,
)
lines(
    0.095,
    0.133,
    ["cyber · HEMP ·", "geomagnetic storms"],
    fontsize=4.1,
    color=GREY,
    style="italic",
    line_h=0.024,
)

# Lower-right circle
ax.text(
    0.897,
    0.200,
    "BIOLOGICAL",
    ha="center",
    va="center",
    fontsize=5.2,
    fontweight="bold",
    color=BIO_DK,
)
lines(
    0.897,
    0.153,
    ["pandemics &", "engineered", "pathogens"],
    fontsize=4.1,
    color=GREY,
    style="italic",
    line_h=0.024,
)

# ---------------------------------------------------------------------------
# Resilience factors — single-set regions
# ---------------------------------------------------------------------------
lines(
    0.5,
    0.720,
    ["Warmer baseline climate,", "Southern-hemisphere", "location"],
    fontsize=4.5,
    color=SUN_DK,
    weight="bold",
    line_h=0.0275,
)

lines(
    0.262,
    0.350,
    ["Hardened, low-tech,", "decentralised", "infrastructure"],
    fontsize=4.5,
    color=INFRA_DK,
    weight="bold",
    line_h=0.0275,
)

lines(
    0.738,
    0.350,
    ["Geographic isolation,", "closable borders,", "strong health system"],
    fontsize=4.5,
    color=BIO_DK,
    weight="bold",
    line_h=0.0275,
)

# ---------------------------------------------------------------------------
# Resilience factors — pairwise lenses
# ---------------------------------------------------------------------------
# ASRS ∩ GCIL
lines(
    0.350,
    0.560,
    ["Resilient food", "production,", "forest cover"],
    fontsize=3.9,
    color=INK,
    weight="bold",
    line_h=0.022,
)

# ASRS ∩ GCBR
lines(
    0.660,
    0.545,
    ["Large and", "modern", "industrial", "base"],
    fontsize=3.9,
    color=INK,
    weight="bold",
    line_h=0.0205,
)

# GCIL ∩ GCBR
lines(
    0.5,
    0.300,
    ["Subsistence farming,", "low-input agriculture,", "low reliance on imports"],
    fontsize=3.7,
    color=INK,
    weight="bold",
    line_h=0.021,
)

# ---------------------------------------------------------------------------
# Centre — factors that help against ALL three families
# ---------------------------------------------------------------------------
lines(
    0.5,
    0.430,
    [
        "Stable democracy,",
        "high state capacity,",
        "low inequality,",
        "food self-sufficiency",
    ],
    fontsize=4.0,
    color=INK,
    weight="bold",
    line_h=0.022,
)

# ---------------------------------------------------------------------------
# Takeaway strip — Australia & New Zealand
# ---------------------------------------------------------------------------
chip(0.035, 0.010, 0.93, 0.092, FOOT_BG)
ax.text(
    0.5, 0.075, "Australia & New Zealand fare best across scenarios",
    ha="center", va="center", fontsize=5.4, fontweight="bold", color=INK,
)
ax.text(
    0.5,
    0.038,
    "— yet stay vulnerable, especially without global cooperation & trade",
    ha="center", va="center", fontsize=4.3, color=GREY,
)

# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------
out_file = output_path / "visual_abstract.png"
fig.savefig(out_file, dpi=600, facecolor="white")
fig.savefig(output_path / "visual_abstract.svg", facecolor="white")
plt.close(fig)
print(f"Saved {out_file}")
