"""
Plot Holocene volcanic eruptions on a world map, colored by VEI.

Reads volcano data from data/volcano_list.csv and creates a map showing
eruption locations as dots. VEI 0-5 shown in yellow, VEI 6 in orange (2x size),
VEI 7 in red (4x size), with volcano names labeled.

Usage:
    python src/plot_volcano_map.py
"""

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
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


def create_volcano_geodataframe(df):
    """Convert volcano dataframe to GeoDataFrame with point geometries."""
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df["Longitude"], df["Latitude"]),
        crs="EPSG:4326",  # WGS84
    )
    return gdf


def plot_volcano_map(volcano_gdf, output_path):
    """
    Create and save the volcano eruption map.

    Parameters
    ----------
    volcano_gdf : GeoDataFrame
        Volcano eruption data with geometry and VEI columns.
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

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_facecolor("white")

    # Plot countries (light gray background)
    world.plot(ax=ax, color="#F5F5F5", edgecolor="#888888", linewidth=0.3)

    # Define VEI groups with colors and sizes
    # Base size for VEI 0-5, then double for each level
    base_size = 60
    vei_groups = [
        {
            "vei_range": (0, 5),
            "color": "#FFD700",
            "size": base_size,
            "label": "VEI 0-5",
        },
        {
            "vei_range": (6, 6),
            "color": "#FF8C00",
            "size": base_size * 3,
            "label": "VEI 6",
        },
        {
            "vei_range": (7, 7),
            "color": "#DC143C",
            "size": base_size * 6,
            "label": "VEI 7",
        },
    ]

    # Plot each VEI group separately
    # Plot in reverse order so larger eruptions appear on top
    for group in vei_groups:
        vei_min, vei_max = group["vei_range"]
        mask = (volcano_gdf["VEI"] >= vei_min) & (volcano_gdf["VEI"] <= vei_max)
        subset = volcano_gdf[mask]

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
                zorder=3,
            )

    # Add labels for VEI 7 eruptions
    vei7_mask = volcano_gdf["VEI"] == 7
    vei7_eruptions = volcano_gdf[vei7_mask]

    # Use adjustText if available, otherwise simple labels with offset
    try:
        from adjustText import adjust_text

        texts = []
        for idx, row in vei7_eruptions.iterrows():
            text = ax.annotate(
                row["Name"],
                xy=(row.geometry.x, row.geometry.y),
                xytext=(8, 8),
                textcoords="offset points",
                fontsize=8,
                color="#333333",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="white",
                    edgecolor="grey",
                    alpha=0.9,
                    linewidth=0.5,
                ),
                zorder=4,
            )
            texts.append(text)

        # Adjust text positions to avoid overlaps
        adjust_text(
            texts, arrowprops=dict(arrowstyle="-", color="#888888", lw=0.5, alpha=0.7)
        )
    except ImportError:
        # Fallback: simple labels with offset
        for idx, row in vei7_eruptions.iterrows():
            ax.annotate(
                row["Name"],
                xy=(row.geometry.x, row.geometry.y),
                xytext=(8, 8),
                textcoords="offset points",
                fontsize=8,
                color="#333333",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor="white",
                    edgecolor="#DC143C",
                    alpha=0.9,
                    linewidth=0.5,
                ),
                zorder=4,
            )

    # Add ALLFED border
    border.plot(ax=ax, edgecolor="black", linewidth=0.5, facecolor="none", zorder=4)

    # Remove axes
    ax.set_axis_off()

    # Add legend (lower left)
    legend = ax.legend(
        loc="lower left",
        frameon=True,
        facecolor="white",
        edgecolor="#888888",
        fontsize=9,
        markerscale=1.5,
    )
    legend.set_zorder(5)

    # Add title
    ax.set_title("Holocene Volcanic Eruptions by Explosivity", fontsize=14, pad=10)

    # Add data summary annotation (lower right to avoid legend overlap)
    n_eruptions = len(volcano_gdf)
    n_volcanoes = volcano_gdf["Name"].nunique()
    ax.annotate(
        f"{n_eruptions:,} eruptions at {n_volcanoes:,} volcanoes",
        xy=(0.98, 0.08),
        xycoords="axes fraction",
        fontsize=9,
        color="#555555",
        ha="right",
    )

    # Add source annotation
    ax.annotate(
        "Data: NOAA NGDC Significant Volcanic Eruptions Database",
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
    output_path = repo_root / "results" / "figures" / "holocene_volcanic_eruptions.png"

    # Verify data file exists
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    # Load data
    print("Loading volcano data...")
    df = load_volcano_data(data_path)
    print(f"Loaded {len(df)} eruptions with valid coordinates and VEI")

    # Print VEI distribution
    print("\nVEI distribution:")
    vei_counts = df["VEI"].value_counts().sort_index()
    for vei, count in vei_counts.items():
        print(f"  VEI {vei}: {count} eruptions")

    # Convert to GeoDataFrame
    volcano_gdf = create_volcano_geodataframe(df)

    # Create map
    print("\nCreating map...")
    fig, ax = plot_volcano_map(volcano_gdf, output_path)

    plt.show()


if __name__ == "__main__":
    main()
