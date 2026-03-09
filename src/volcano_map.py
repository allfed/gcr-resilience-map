"""
Plot volcanic eruptions on a world map, colored by VEI.

Reads Holocene eruption data from data/volcano_list.csv (VEI 0-7) and
large-eruption data from data/mag 7 and above eruptions.xlsx (VEI 8, covering
~2.5 million years). VEI 0-5 shown in yellow, VEI 6 in orange, VEI 7 in red,
VEI 8 in dark purple, with names labeled for VEI >= 7.

Usage:
    python src/volcano_map.py
"""

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import warnings
from pathlib import Path

# Apply ALLFED style
plt.style.use(
    "https://raw.githubusercontent.com/allfed/ALLFED-matplotlib-style-sheet/main/ALLFED.mplstyle"
)


def load_volcano_data(filepath):
    """
    Load and clean volcano eruption data from CSV file.

    Handles the NOAA NGDC format which has:
    - A "Search Parameters" row at the top
    - Quoted column headers
    - Eruption data rows

    Filters to eruptions with valid coordinates and VEI values.
    """
    # Read with skiprows=1 to skip the search parameters row
    df = pd.read_csv(filepath, sep=",")

    # Strip quotes from column names if present
    df.columns = df.columns.str.strip('"')

    # Keep only rows with valid coordinates and VEI
    df = df.dropna(subset=["Latitude", "Longitude", "VEI"])

    # Ensure numeric types
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df["VEI"] = pd.to_numeric(df["VEI"], errors="coerce")

    # Drop any rows that couldn't be converted
    df = df.dropna(subset=["Latitude", "Longitude", "VEI"])

    # Convert VEI to integer
    df["VEI"] = df["VEI"].astype(int)

    # Strip quotes from string columns if present
    if "Name" in df.columns:
        df["Name"] = df["Name"].astype(str).str.strip('"')

    return df


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

    Note: The border.geojson file coordinates are already in Winkel Tripel
    projection despite the CRS metadata saying WGS84.
    """
    url = (
        "https://raw.githubusercontent.com/ALLFED/ALLFED-map-border/main/border.geojson"
    )
    border = gpd.read_file(url)
    # Override CRS to match actual projection
    border = border.set_crs("+proj=wintri", allow_override=True)
    return border


def load_vei8_data(filepath):
    """
    Load VEI 8 eruptions from the large-eruptions Excel file.

    Covers ~2.5 million years. Returns only VEI 8 rows with valid coordinates.
    """
    df = pd.read_excel(filepath)
    df = df.rename(columns={"Volcano Name": "Name"})
    df = df[["Name", "Latitude", "Longitude", "VEI"]].copy()
    df = df.dropna(subset=["Latitude", "Longitude", "VEI"])
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    df["VEI"] = pd.to_numeric(df["VEI"], errors="coerce").astype(int)
    df = df[df["VEI"] == 8]
    return df


def create_volcano_geodataframe(df):
    """Convert volcano dataframe to GeoDataFrame with point geometries."""
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
        crs="EPSG:4326",  # WGS84
    )
    return gdf


def plot_volcano_map(volcano_gdf, vei8_gdf, output_path):
    """
    Create and save the volcano eruption map.

    Parameters
    ----------
    volcano_gdf : GeoDataFrame
        Holocene eruption data (VEI 0-7) with geometry and VEI columns.
    vei8_gdf : GeoDataFrame
        VEI 8 eruption data (~2.5 Ma) with geometry and VEI columns.
    output_path : Path
        Where to save the output figure.

    Returns
    -------
    fig, ax : matplotlib figure and axes
    """
    # Load base layers
    world = load_world_data()
    border = load_border()

    # Reproject to Winkel Tripel
    world = world.to_crs("+proj=wintri")
    volcano_gdf = volcano_gdf.to_crs("+proj=wintri")
    vei8_gdf = vei8_gdf.to_crs("+proj=wintri")

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_facecolor("white")

    # Plot countries (light gray background)
    world.plot(ax=ax, color="#F5F5F5", edgecolor="#888888", linewidth=0.3)

    # Define VEI groups with colors and sizes (plotted smallest to largest so
    # bigger eruptions render on top). VEI 7 is plotted again at a higher
    # zorder after VEI 8 so the labeled dots are always on top.
    base_size = 60
    vei_groups = [
        {
            "gdf": volcano_gdf,
            "vei_range": (0, 5),
            "color": "#FFD700",
            "size": base_size,
            "label": "VEI 0–5 (Holocene)",
            "zorder": 3,
        },
        {
            "gdf": volcano_gdf,
            "vei_range": (6, 6),
            "color": "#FF8C00",
            "size": base_size * 3,
            "label": "VEI 6 (Holocene)",
            "zorder": 3,
        },
        {
            "gdf": vei8_gdf,
            "vei_range": (8, 8),
            "color": "#4B0082",
            "size": base_size * 9,
            "label": "VEI 8 (~2.5 Ma)",
            "zorder": 4,
        },
        # VEI 7 plotted last so it sits on top of VEI 8 dots
        {
            "gdf": volcano_gdf,
            "vei_range": (7, 7),
            "color": "#DC143C",
            "size": base_size * 6,
            "label": "VEI 7 (Holocene)",
            "zorder": 5,
        },
    ]

    for group in vei_groups:
        vei_min, vei_max = group["vei_range"]
        mask = (group["gdf"]["VEI"] >= vei_min) & (group["gdf"]["VEI"] <= vei_max)
        subset = group["gdf"][mask]

        if len(subset) > 0:
            ax.scatter(
                subset.geometry.x,
                subset.geometry.y,
                c=group["color"],
                s=group["size"],
                alpha=1,
                edgecolor="black",
                linewidth=0.3,
                label=group["label"],
                zorder=group["zorder"],
            )

    # Label Holocene VEI 7 eruptions only
    vei7_eruptions = volcano_gdf[volcano_gdf["VEI"] == 7]

    try:
        from adjustText import adjust_text

        texts = []
        for _, row in vei7_eruptions.iterrows():
            text = ax.annotate(
                row["Name"],
                xy=(row.geometry.x, row.geometry.y),
                xytext=(8, 8),
                textcoords="offset points",
                fontsize=7,
                color="#333333",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="white",
                    edgecolor="#DC143C",
                    alpha=0.9,
                    linewidth=0.5,
                ),
                zorder=5,
            )
            texts.append(text)

        adjust_text(
            texts, arrowprops=dict(arrowstyle="-", color="#888888", lw=0.5, alpha=0.7)
        )
    except ImportError:
        for _, row in vei7_eruptions.iterrows():
            ax.annotate(
                row["Name"],
                xy=(row.geometry.x, row.geometry.y),
                xytext=(8, 8),
                textcoords="offset points",
                fontsize=7,
                color="#333333",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="white",
                    edgecolor="#DC143C",
                    alpha=0.9,
                    linewidth=0.5,
                ),
                zorder=5,
            )

    # Add ALLFED border
    border.plot(ax=ax, edgecolor="black", linewidth=0.5, facecolor="none", zorder=6)

    # Remove axes
    ax.set_axis_off()

    # Build legend with explicit proxy handles so marker sizes are bounded
    from matplotlib.lines import Line2D

    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#FFD700",
               markeredgecolor="black", markeredgewidth=0.3, markersize=6,
               label="VEI 0–5 (Holocene)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#FF8C00",
               markeredgecolor="black", markeredgewidth=0.3, markersize=9,
               label="VEI 6 (Holocene)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#DC143C",
               markeredgecolor="black", markeredgewidth=0.3, markersize=12,
               label="VEI 7 (Holocene)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#4B0082",
               markeredgecolor="black", markeredgewidth=0.3, markersize=15,
               label="VEI 8 (~2.5 Ma)"),
    ]
    legend = ax.legend(
        handles=legend_elements,
        loc="lower left",
        frameon=True,
        facecolor="white",
        edgecolor="#888888",
        fontsize=9,
    )
    legend.set_zorder(7)

    ax.set_title(
        "Volcanic Eruptions by Explosivity (VEI 0–8)", fontsize=14, pad=10
    )

    # Add source annotation
    ax.annotate(
        "Data: NOAA NGDC (Holocene); LaMEVE database (VEI 8, ~2.5 Ma)",
        xy=(0.98, 0.02),
        xycoords="axes fraction",
        fontsize=8,
        color="#888888",
        ha="right",
    )

    plt.tight_layout()

    # Save figure
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"Map saved to {output_path}")

    return fig, ax


def main():
    # Paths (script is in src folder, data is in data folder)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    data_path = repo_root / "data" / "volcano_list.csv"
    vei8_path = repo_root / "data" / "mag 7 and above eruptions.xlsx"
    output_path = repo_root / "results" / "figures" / "holocene_volcanic_eruptions.png"

    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    if not vei8_path.exists():
        raise FileNotFoundError(f"Data file not found: {vei8_path}")

    # Load Holocene data (VEI 0-7)
    print("Loading Holocene volcano data...")
    df = load_volcano_data(data_path)
    print(f"Loaded {len(df)} Holocene eruptions with valid coordinates and VEI")

    print("\nHolocene VEI distribution:")
    for vei, count in df["VEI"].value_counts().sort_index().items():
        print(f"  VEI {vei}: {count} eruptions")

    volcano_gdf = create_volcano_geodataframe(df)

    # Load VEI 8 data (~2.5 Ma)
    print("\nLoading VEI 8 eruption data...")
    vei8_df = load_vei8_data(vei8_path)
    print(f"Loaded {len(vei8_df)} VEI 8 eruptions")

    vei8_gdf = create_volcano_geodataframe(vei8_df)

    # Create map
    print("\nCreating map...")
    fig, ax = plot_volcano_map(volcano_gdf, vei8_gdf, output_path)

    plt.show()


if __name__ == "__main__":
    main()
