"""
Factor count comparison plots.

Reads the GCR resilience evidence ledger and produces, for several GCR scopes,
a stacked bar chart of the five countries with the most resilience factors.

For every scope (all GCR pooled, then ASRS / GCIL / GCBR individually) the chart
shows, per country:
    * resilience factors above the x-axis (split into named vs. inferred)
    * vulnerability factors below the x-axis (split into named vs. inferred)

Some ledger rows refer to regions rather than single countries. Those rows are
expanded onto every constituent country listed in ``REGION_TO_COUNTRIES`` so the
region's factor is counted for each of its members. Regions with no constituent
country in the ledger (or vague climatic regions) simply contribute nothing to
the country-level counts.

Output: one PNG per scope in ``results/figures/``.
"""

import matplotlib.pyplot as plt
import pandas as pd

# Apply ALLFED style (same as the other plotting scripts in this repo)
plt.style.use(
    "https://raw.githubusercontent.com/allfed/ALLFED-matplotlib-style-sheet/main/ALLFED.mplstyle"
)

LEDGER_PATH = "results/Data/gcr_resilience_evidence_ledger.xlsx"
FIGURE_DIR = "results/figures"

# Region entries in the ledger expanded onto the constituent countries that are
# themselves individually present in the ledger. Edit freely. Regions left out
# (e.g. vague climatic zones such as "Mediterranean climate zones" or
# "Asian monsoon regions") contribute nothing to the country-level counts.
REGION_TO_COUNTRIES = {
    "European Union": ["France", "Germany", "Ireland", "Sweden"],
    "Central Europe": ["Germany", "Switzerland"],
    "Eastern Europe": ["Ukraine", "Russia"],
    "Scandinavia": ["Norway", "Sweden"],
    "Baltics": [],  # Estonia/Latvia/Lithuania - none individually in the ledger
    "Latin America": [
        "Argentina",
        "Bolivia",
        "Brazil",
        "Chile",
        "Colombia",
        "Cuba",
        "Peru",
        "Uruguay",
    ],
    "Southern Africa & South America": [
        "Argentina",
        "Bolivia",
        "Brazil",
        "Chile",
        "Colombia",
        "Peru",
        "Uruguay",
    ],
    "Middle East": ["Iran", "Israel"],
    "Africa": [],  # no individual African country present in the ledger
    "Sub-Saharan Africa": [],
    "Asian monsoon regions": [],  # climatic, no clean membership
    "Mediterranean climate zones": [],  # climatic, no clean membership
}

# Scopes to plot: label -> GCR categories to include (None = all categories
# pooled). The hazard-specific scopes also include the "General" factors, which
# are cross-cutting and not tied to a single hazard.
SCOPES = {
    "All GCR": None,
    "ASRS": ["ASRS", "General"],
    "GCIL": ["GCIL", "General"],
    "GCBR": ["GCBR", "General"],
}

# Colours for the four stacked segments. A blue (resilience) vs. orange
# (vulnerability) diverging scheme: colour-blind friendly (avoids the red/green
# pitfall) and reuses the blue/amber hues from visual_abstract.py. Named vs.
# inferred is a dark/light luminance step within each hue, which also reads
# under colour-blindness.
COLORS = {
    ("resilient", "named"): "#205089",  # dark blue
    ("resilient", "inference"): "#92c0e8",  # light blue
    ("vulnerable", "named"): "#a55f0c",  # dark orange
    ("vulnerable", "inference"): "#f5c089",  # light orange
}

LEGEND_LABELS = {
    ("resilient", "named"): "Resilience - named",
    ("resilient", "inference"): "Resilience - inferred",
    ("vulnerable", "named"): "Vulnerability - named",
    ("vulnerable", "inference"): "Vulnerability - inferred",
}

N_TOP = 5


def load_ledger(path=LEDGER_PATH):
    """Load the ledger and drop the embedded legend/notes rows and mixed factors."""
    df = pd.read_excel(path, sheet_name="Ledger")
    # The bottom rows of the sheet are an embedded legend with no country.
    df = df[df["Country"].notna()].copy()
    # Keep only clear resilient / vulnerable factors with a known provenance.
    df = df[df["Direction"].isin(["resilient", "vulnerable"])]
    df = df[df["Provenance"].isin(["named", "inference"])]
    return df


def expand_regions(df):
    """Replace region rows with one row per constituent country.

    Rows whose ``Country`` is an individual country are kept as-is. Rows whose
    ``Country`` is a known region are duplicated onto each constituent country.
    Unknown regions (no mapping / empty mapping) are dropped from the country
    level analysis.
    """
    rows = []
    for _, row in df.iterrows():
        country = row["Country"]
        if country in REGION_TO_COUNTRIES:
            for member in REGION_TO_COUNTRIES[country]:
                new_row = row.copy()
                new_row["Country"] = member
                rows.append(new_row)
        else:
            rows.append(row)
    return pd.DataFrame(rows, columns=df.columns)


def counts_by_country(df):
    """Return a per-country count table with the four (direction, provenance) buckets."""
    table = (
        df.groupby(["Country", "Direction", "Provenance"])
        .size()
        .unstack(["Direction", "Provenance"], fill_value=0)
    )
    # Ensure all four buckets exist as columns.
    for key in COLORS:
        if key not in table.columns:
            table[key] = 0
    return table


def top_countries(table):
    """Top N countries ranked by total resilience factors (named + inferred)."""
    resilience_total = (
        table[("resilient", "named")] + table[("resilient", "inference")]
    )
    resilience_total = resilience_total[resilience_total > 0]
    ranked = resilience_total.sort_values(ascending=False)
    return list(ranked.head(N_TOP).index)


def plot_scope(table, countries, scope_label, out_path):
    """Draw and save the diverging stacked bar chart for one scope."""
    fig, ax = plt.subplots(figsize=(9, 6))

    x = range(len(countries))

    # Resilience above the axis (named at bottom, inferred stacked on top).
    res_named = [table.loc[c, ("resilient", "named")] for c in countries]
    res_inf = [table.loc[c, ("resilient", "inference")] for c in countries]
    ax.bar(
        x,
        res_named,
        color=COLORS[("resilient", "named")],
        label=LEGEND_LABELS[("resilient", "named")],
    )
    ax.bar(
        x,
        res_inf,
        bottom=res_named,
        color=COLORS[("resilient", "inference")],
        label=LEGEND_LABELS[("resilient", "inference")],
    )

    # Vulnerability below the axis (named first going down, inferred below it).
    vul_named = [-table.loc[c, ("vulnerable", "named")] for c in countries]
    vul_inf = [-table.loc[c, ("vulnerable", "inference")] for c in countries]
    ax.bar(
        x,
        vul_named,
        color=COLORS[("vulnerable", "named")],
        label=LEGEND_LABELS[("vulnerable", "named")],
    )
    ax.bar(
        x,
        vul_inf,
        bottom=vul_named,
        color=COLORS[("vulnerable", "inference")],
        label=LEGEND_LABELS[("vulnerable", "inference")],
    )

    ax.axhline(0, color="black", linewidth=1)
    ax.set_xticks(list(x))
    ax.set_xticklabels(countries, rotation=30, ha="right")
    ax.set_ylabel("Number of vulnerability / resilience factors")
    ax.set_title(f"Top {len(countries)} countries by resilience factors - {scope_label}")
    # Show absolute counts on both sides of the axis (vulnerability is drawn below
    # zero but labelled with positive numbers).
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda value, _pos: f"{abs(value):g}")
    )
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.grid(False, axis="x")
    ax.legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {out_path}  (countries: {', '.join(countries)})")


def main():
    df = load_ledger()
    df = expand_regions(df)

    for scope_label, categories in SCOPES.items():
        scoped = df if categories is None else df[df["GCR category"].isin(categories)]
        table = counts_by_country(scoped)
        countries = top_countries(table)
        if not countries:
            print(f"No resilience factors for scope '{scope_label}', skipping.")
            continue
        slug = scope_label.lower().replace(" ", "_")
        out_path = f"{FIGURE_DIR}/factor_count_{slug}.png"
        plot_scope(table, countries, scope_label, out_path)


if __name__ == "__main__":
    main()
