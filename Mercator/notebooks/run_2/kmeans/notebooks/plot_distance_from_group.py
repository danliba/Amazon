"""Rank every k=50 cluster by its centroid distance from one reference group.

Same metric as notebook 1.5 cell 16: Euclidean distance between two full
centroid tracks in degrees, i.e. sqrt(sum over all (lat, lon) of all days).
The reference is the mean centroid track of the clusters in REF_GROUP, so a
multi-cluster group is represented once rather than arbitrarily by a member.

Reads the saved fit, so it never refits.
"""
import sys, os
sys.path.insert(0, os.path.abspath(".."))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import config as C

REF_GROUP = "A1"          # change to rank distances from any other group

# current grouping, notebook 1.5 cell 13
ASSIGN = {
    0:"A2",  1:"E1",  2:"B1",  3:"BS",  4:"E2",  5:"A2",  6:"C",   7:"B2",  8:"F",   9:"S",
   10:"B2", 11:"B3", 12:"C",  13:"B2", 14:"F",  15:"S",  16:"A1", 17:"BS", 18:"E",  19:"S",
   20:"A2", 21:"E0", 22:"A2", 23:"B2", 24:"B3", 25:"S",  26:"CB", 27:"E2", 28:"B2", 29:"B2",
   30:"C",  31:"A1", 32:"E",  33:"A3", 34:"B2", 35:"A12",36:"A2", 37:"S",  38:"B2", 39:"A2",
   40:"B1", 41:"S",  42:"A2", 43:"BS", 44:"C",  45:"F",  46:"B2", 47:"CB", 48:"B1", 49:"E1",
}

cent_deg = np.load(C.MODELS_DIR / "manual_1.5_k50" / "centroids_deg.npy")
K = len(cent_deg)

ref_members = [c for c in range(K) if ASSIGN[c] == REF_GROUP]
ref = cent_deg[ref_members].mean(axis=0)
dist = np.sqrt(((cent_deg - ref) ** 2).sum(axis=1))

order = np.argsort(dist)                      # nearest at the top of the chart

print(f"distance from group {REF_GROUP} (clusters {ref_members}), degrees\n")
print(" rank  cluster  group   dist")
for r, c in enumerate(order, 1):
    mark = " <-- ref" if c in ref_members else ""
    print(f" {r:4d}  {c:7d}  {ASSIGN[c]:5s} {dist[c]:6.1f}{mark}")

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"

fig, ax = plt.subplots(figsize=(7.5, 11))
fig.patch.set_facecolor(SURFACE)
ax.set_facecolor(SURFACE)

y = np.arange(K)
colors = [ORANGE if c in ref_members else BLUE for c in order]
ax.hlines(y, 0, dist[order], color=colors, lw=2, alpha=.55, zorder=2)
ax.scatter(dist[order], y, s=42, color=colors, zorder=3,
           edgecolor=SURFACE, linewidth=1)

ax.set_yticks(y)
ax.set_yticklabels([f"{c}  ({ASSIGN[c]})" for c in order], fontsize=8, color=INK)
ax.invert_yaxis()
ax.set_xlabel(f"centroid distance from group {REF_GROUP}  (degrees)",
              fontsize=9, color=MUTED)
ax.set_xlim(0, dist.max() * 1.05)
ax.margins(y=.01)

ax.xaxis.grid(True, color="0.88", lw=.6)
ax.set_axisbelow(True)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color("0.8")
ax.tick_params(axis="x", colors=MUTED, labelsize=8, length=0)
ax.tick_params(axis="y", length=0)

ax.scatter([], [], s=42, color=ORANGE, label=f"group {REF_GROUP} (reference)")
ax.scatter([], [], s=42, color=BLUE, label="other clusters")
ax.legend(loc="upper right", frameon=False, fontsize=8, labelcolor=MUTED)

ax.set_title(f"k=50 clusters ranked by centroid distance from group {REF_GROUP}",
             fontsize=11, color=INK, pad=12, loc="left")

fig.tight_layout()
out = f"distance_from_{REF_GROUP}"
fig.savefig(out + ".png", dpi=150, bbox_inches="tight", facecolor=SURFACE)
fig.savefig(out + ".pdf", bbox_inches="tight", facecolor=SURFACE)
print(f"\nwrote {out}.png / {out}.pdf")
