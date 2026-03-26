"""
Plot volcanic eruptions on a world map, colored by VEI.

Primary source: GVP_Eruption_Search_Result.xlsx (Global Volcanism Program),
filtered to the last MAX_YEARS years. VEI 7+ eruptions are cross-checked against
data/mag 7 and above eruptions.xlsx (LaMEVE) and any missing events are appended.

VEI 0-5 shown in yellow, VEI 6 in orange, VEI 7 in red, with names labeled
for VEI >= 7.

Usage:
    python src/volcano_map.py
"""

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import warnings
from pathlib import Path
from adjustText import adjust_text

# Apply ALLFED style
plt.style.use(
    "https://raw.githubusercontent.com/allfed/ALLFED-matplotlib-style-sheet/main/ALLFED.mplstyle"
)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_gvp(filepath, max_years=11_700):
    """
    Load the GVP eruption search result (main source).

    Filters to confirmed eruptions within the last `max_years` years and with
    valid coordinates and VEI. Eruptions with known VEI estimates that GVP
    leaves blank are patched before NaN rows are dropped.
    """
    df = pd.read_excel(filepath, sheet_name="Eruption List", header=1)
    df = df.rename(columns={"Volcano Name": "Name"})
    df["VEI"] = pd.to_numeric(df["VEI"], errors="coerce")
    df["Start Year"] = pd.to_numeric(df["Start Year"], errors="coerce")
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    # Patch known large eruptions that GVP lists without a VEI
    # Kuwae ~1453 CE (GVP Start Year 1425): widely estimated VEI 6
    df.loc[(df["Name"] == "Kuwae") & (df["Start Year"] == 1425), "VEI"] = 6

    df = df.dropna(subset=["Latitude", "Longitude", "VEI", "Start Year"])
    cutoff_year = 2025 - max_years
    df = df[df["Start Year"] >= cutoff_year]
    df["VEI"] = df["VEI"].astype(int)
    return df[["Name", "Latitude", "Longitude", "VEI", "Start Year"]].copy()


def load_lameve(filepath, max_years=11_700):
    """
    Load VEI 7+ eruptions from the LaMEVE Excel file for cross-checking.

    LaMEVE uses BP relative to 1950, so Year = 1950 - Year BP.
    """
    df = pd.read_excel(filepath)
    df = df.rename(columns={"Volcano Name": "Name"})
    df["VEI"] = pd.to_numeric(df["VEI"], errors="coerce")
    df["Year BP"] = pd.to_numeric(df["Year BP"], errors="coerce")
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df = df.dropna(subset=["Latitude", "Longitude", "VEI", "Year BP"])
    df = df[df["VEI"] >= 7]
    df = df[df["Year BP"] <= max_years]
    df["Start Year"] = 1950 - df["Year BP"]
    df["VEI"] = df["VEI"].astype(int)
    # Drop duplicate entries for the same volcano/eruption (same name + coords)
    df = df.drop_duplicates(subset=["Name", "Latitude", "Longitude", "VEI"])
    return df[["Name", "Latitude", "Longitude", "VEI", "Start Year"]].copy()


def merge_sources(gvp_df, lameve_df, coord_tol=1.0):
    """
    Append LaMEVE VEI 7+ events that are not already in the GVP dataset.

    Two events are considered the same if their coordinates are within
    `coord_tol` degrees of each other (handles name differences between
    databases).
    """
    gvp_large = gvp_df[gvp_df["VEI"] >= 7][["Latitude", "Longitude"]].values
    missing_rows = []
    for _, row in lameve_df.iterrows():
        if len(gvp_large) > 0:
            lat_ok = abs(gvp_large[:, 0] - row["Latitude"]) < coord_tol
            lon_ok = abs(gvp_large[:, 1] - row["Longitude"]) < coord_tol
            if (lat_ok & lon_ok).any():
                continue  # already present
        missing_rows.append(row)
        print(f"  Adding from LaMEVE (not in GVP): {row['Name']} "
              f"(~{int(row['Start Year'])} CE, VEI {row['VEI']})")

    if missing_rows:
        extra = pd.DataFrame(missing_rows)
        return pd.concat([gvp_df, extra], ignore_index=True)
    return gvp_df


# Names to use on the map, keyed by the database name.
# Chosen to match the most widely used name in the scientific literature.
NAME_OVERRIDES = {
    "Fisher": "Fisher Caldera",
    "Blanco, Cerro": "Cerro Blanco",
    "Rinjani": "Samalas",   # 1257 CE eruption originated from the Samalas vent
}


def apply_name_overrides(df):
    df = df.copy()
    df["Name"] = df["Name"].replace(NAME_OVERRIDES)
    return df


# ---------------------------------------------------------------------------
# Map helpers
# ---------------------------------------------------------------------------

def load_world_data():
    """Load Natural Earth country boundaries."""
    url = (
        "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
    )
    try:
        world = gpd.read_file(url)
    except Exception:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
    return world


def load_border():
    """
    Load ALLFED map border.

    Note: The border.geojson coordinates are already in Winkel Tripel
    projection despite the CRS metadata saying WGS84.
    """
    url = (
        "https://raw.githubusercontent.com/ALLFED/ALLFED-map-border/main/border.geojson"
    )
    border = gpd.read_file(url)
    border = border.set_crs("+proj=wintri", allow_override=True)
    return border


def to_geodataframe(df):
    """Convert a dataframe with Latitude/Longitude to a projected GeoDataFrame."""
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
        crs="EPSG:4326",
    )
    return gdf.to_crs("+proj=wintri")


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_volcano_map(gdf, output_path, max_years=10_000):
    """
    Create and save the volcano eruption map.

    Parameters
    ----------
    gdf : GeoDataFrame
        Eruption data in Winkel Tripel projection with VEI and Name columns.
    output_path : Path
        Where to save the output figure.
    max_years : int
        Time window used (for title and source label).
    """
    world = load_world_data().to_crs("+proj=wintri")
    border = load_border()

    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_facecolor("white")
    world.plot(ax=ax, color="#F5F5F5", edgecolor="#888888", linewidth=0.3)

    base_size = 60
    vei_groups = [
        {"vei_range": (0, 5), "color": "#FFD700", "size": base_size,
         "label": "VEI 0–5", "zorder": 3},
        {"vei_range": (6, 6), "color": "#FF8C00", "size": base_size * 3,
         "label": "VEI 6", "zorder": 4},
        {"vei_range": (7, 7), "color": "#DC143C", "size": base_size * 6,
         "label": "VEI 7", "zorder": 5},
    ]

    for group in vei_groups:
        vei_min, vei_max = group["vei_range"]
        subset = gdf[(gdf["VEI"] >= vei_min) & (gdf["VEI"] <= vei_max)]
        if len(subset) > 0:
            ax.scatter(
                subset.geometry.x, subset.geometry.y,
                c=group["color"], s=group["size"],
                edgecolor="black", linewidth=0.3,
                label=group["label"], zorder=group["zorder"],
            )

    # --- Labels for VEI 7 ---
    vei7 = gdf[gdf["VEI"] == 7].copy()

    # Volcanoes that are pinned manually (close neighbours that need explicit
    # left/right placement so it is clear which label belongs to which dot).
    # Format: name -> (ha, x_offset_pts, y_offset_pts)
    PINNED = {
        "Samalas": ("right", -8, 6),   # Lombok — label to the left
        "Tambora": ("left",   8, 6),   # Sumbawa — label to the right
    }

    bbox_style = dict(
        boxstyle="round,pad=0.25",
        facecolor="white",
        edgecolor="#DC143C",
        alpha=0.9,
        linewidth=0.5,
    )

    # Draw pinned labels with annotate so the connector arrow is anchored
    pinned_names = set(PINNED)
    pinned_rows = vei7[vei7["Name"].isin(pinned_names)]
    for _, row in pinned_rows.iterrows():
        ha, dx, dy = PINNED[row["Name"]]
        ax.annotate(
            row["Name"],
            xy=(row.geometry.x, row.geometry.y),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=7,
            color="#333333",
            ha=ha,
            bbox=bbox_style,
            arrowprops=dict(arrowstyle="-", color="#888888", lw=0.6, alpha=0.8),
            zorder=9,
        )

    # Re-plot the pinned dots on top so they sit above the annotation arrows
    ax.scatter(
        pinned_rows.geometry.x, pinned_rows.geometry.y,
        c="#DC143C", s=base_size * 6,
        edgecolor="black", linewidth=0.3,
        zorder=10,
    )

    # Auto-place the remaining labels with adjust_text
    auto = vei7[~vei7["Name"].isin(pinned_names)]
    texts = []
    for _, row in auto.iterrows():
        t = ax.text(
            row.geometry.x, row.geometry.y,
            row["Name"],
            fontsize=7,
            color="#333333",
            bbox=bbox_style,
            zorder=9,
        )
        texts.append(t)

    adjust_text(
        texts,
        ax=ax,
        x=vei7.geometry.x.values,
        y=vei7.geometry.y.values,
        expand=(1.6, 2.0),
        arrowprops=dict(arrowstyle="-", color="#888888", lw=0.6, alpha=0.8),
        force_text=(0.5, 0.8),
        force_static=(0.2, 0.4),
    )

    border.plot(ax=ax, edgecolor="black", linewidth=0.5, facecolor="none", zorder=2)
    ax.set_axis_off()

    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#FFD700",
               markeredgecolor="black", markeredgewidth=0.3, markersize=6,
               label="VEI 0–5"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#FF8C00",
               markeredgecolor="black", markeredgewidth=0.3, markersize=9,
               label="VEI 6"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#DC143C",
               markeredgecolor="black", markeredgewidth=0.3, markersize=12,
               label="VEI 7"),
    ]
    legend = ax.legend(
        handles=legend_elements, loc="lower left", frameon=True,
        facecolor="white", edgecolor="#888888", fontsize=9,
    )
    legend.set_zorder(10)

    ax.set_title(
        f"Volcanic Eruptions by Explosivity — Last {max_years:,} Years",
        fontsize=14, pad=10,
    )
    ax.annotate(
        "Data: GVP Volcanoes of the World v5.2.8; supplemented by LaMEVE (VEI 7+)",
        xy=(0.98, 0.02), xycoords="axes fraction",
        fontsize=8, color="#888888", ha="right",
    )

    plt.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"Map saved to {output_path}")
    return fig, ax


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # --- Configuration ---
    MAX_YEARS = 11_700  # years to look back from present

    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    gvp_path = repo_root / "data" / "GVP_Eruption_Search_Result.xlsx"
    lameve_path = repo_root / "data" / "mag 7 and above eruptions.xlsx"
    output_path = repo_root / "results" / "figures" / "holocene_volcanic_eruptions.png"

    for p in [gvp_path, lameve_path]:
        if not p.exists():
            raise FileNotFoundError(f"Data file not found: {p}")

    print(f"Loading GVP data (last {MAX_YEARS:,} years)...")
    gvp_df = load_gvp(gvp_path, max_years=MAX_YEARS)
    print(f"  {len(gvp_df)} eruptions — VEI distribution: "
          f"{gvp_df['VEI'].value_counts().sort_index().to_dict()}")

    print(f"\nLoading LaMEVE VEI 7+ for cross-check (last {MAX_YEARS:,} years)...")
    lameve_df = load_lameve(lameve_path, max_years=MAX_YEARS)
    print(f"  {len(lameve_df)} records")

    print("\nCross-checking sources...")
    merged_df = merge_sources(gvp_df, lameve_df)
    merged_df = apply_name_overrides(merged_df)
    print(f"  Final dataset: {len(merged_df)} eruptions")
    print(f"  VEI distribution: {merged_df['VEI'].value_counts().sort_index().to_dict()}")

    print("\nCreating map...")
    gdf = to_geodataframe(merged_df)
    fig, ax = plot_volcano_map(gdf, output_path, max_years=MAX_YEARS)

    plt.show()


if __name__ == "__main__":
    main()
