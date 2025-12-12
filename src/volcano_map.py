"""
Plot Holocene volcanic eruptions on a world map, colored by VEI.

Reads volcano data from data/volcano_list.tsv and creates a map showing
eruption locations as dots colored by Volcanic Explosivity Index (VEI).

Usage:
    python src/plot_volcano_map.py
"""

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from matplotlib.cm import ScalarMappable
import numpy as np
import warnings
from pathlib import Path

# Apply ALLFED style
plt.style.use("https://raw.githubusercontent.com/allfed/ALLFED-matplotlib-style-sheet/main/ALLFED.mplstyle")


def load_volcano_data(filepath):
    """
    Load and clean volcano eruption data from TSV file.
    
    Handles the NOAA NGDC format which has:
    - A "Search Parameters" row at the top
    - Quoted column headers
    - Eruption data rows
    
    Filters to eruptions with valid coordinates and VEI values.
    """
    # Read with skiprows=1 to skip the search parameters row
    df = pd.read_csv(filepath, sep=',')
    
    # Strip quotes from column names if present
    df.columns = df.columns.str.strip('"')
    
    # Keep only rows with valid coordinates and VEI
    df = df.dropna(subset=['Latitude', 'Longitude', 'VEI'])
    
    # Ensure numeric types
    df['Latitude'] = pd.to_numeric(df['Latitude'], errors='coerce')
    df['Longitude'] = pd.to_numeric(df['Longitude'], errors='coerce')
    df['VEI'] = pd.to_numeric(df['VEI'], errors='coerce')
    
    # Drop any rows that couldn't be converted
    df = df.dropna(subset=['Latitude', 'Longitude', 'VEI'])
    
    # Convert VEI to integer
    df['VEI'] = df['VEI'].astype(int)
    
    # Strip quotes from string columns if present
    if 'Name' in df.columns:
        df['Name'] = df['Name'].astype(str).str.strip('"')
    
    return df


def load_world_data():
    """Load Natural Earth country boundaries."""
    url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
    try:
        world = gpd.read_file(url)
    except Exception:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
    return world


def load_border():
    """
    Load ALLFED map border.
    
    Note: The border.geojson file coordinates are already in Winkel Tripel 
    projection despite the CRS metadata saying WGS84.
    """
    url = 'https://raw.githubusercontent.com/ALLFED/ALLFED-map-border/main/border.geojson'
    border = gpd.read_file(url)
    # Override CRS to match actual projection
    border = border.set_crs('+proj=wintri', allow_override=True)
    return border


def create_volcano_geodataframe(df):
    """Convert volcano dataframe to GeoDataFrame with point geometries."""
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df['Longitude'], df['Latitude']),
        crs='EPSG:4326'  # WGS84
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
    world = world.to_crs('+proj=wintri')
    volcano_gdf = volcano_gdf.to_crs('+proj=wintri')
    
    # Set up VEI colormap
    # VEI ranges 0-7, using Yellow-Orange-Red for intuitive severity mapping
    vei_min, vei_max = 0, 7
    vei_levels = np.arange(vei_min, vei_max + 2)  # Boundaries: 0,1,2,3,4,5,6,7,8
    cmap = plt.cm.YlOrRd
    norm = BoundaryNorm(vei_levels, cmap.N)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))
    ax.set_facecolor('white')
    
    # Plot countries (light gray background)
    world.plot(ax=ax, color='#F5F5F5', edgecolor='#888888', linewidth=0.3)
    
    # Sort by VEI so larger eruptions are plotted on top
    volcano_gdf = volcano_gdf.sort_values('VEI')
    
    # Size scales with VEI for better visibility of large eruptions
    sizes = 50 + volcano_gdf['VEI'] * 10
    
    # Plot volcano points
    scatter = ax.scatter(
        volcano_gdf.geometry.x,
        volcano_gdf.geometry.y,
        c=volcano_gdf['VEI'],
        cmap=cmap,
        norm=norm,
        s=sizes,
        alpha=0.75,
        edgecolor='black',
        linewidth=0.3,
        zorder=3
    )
    
    # Add ALLFED border
    border.plot(ax=ax, edgecolor='black', linewidth=0.5, facecolor='none', zorder=4)
    
    # Remove axes
    ax.set_axis_off()
    
    # Add colorbar
    sm = ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(
        sm,
        ax=ax,
        orientation='horizontal',
        fraction=0.03,
        pad=0.02,
        aspect=30,
        ticks=np.arange(vei_min, vei_max + 1) + 0.5  # Center ticks in each color band
    )
    cbar.ax.set_xticklabels(range(vei_min, vei_max + 1))  # Label with actual VEI values
    cbar.set_label('Volcanic Explosivity Index (VEI)', fontsize=10)
    cbar.ax.tick_params(labelsize=9, which='both', length=0, width=0)
    
    # Add title
    ax.set_title('Holocene Volcanic Eruptions by Explosivity', fontsize=14, pad=10)
    
    # Add data summary annotation
    n_eruptions = len(volcano_gdf)
    n_volcanoes = volcano_gdf['Name'].nunique()
    ax.annotate(
        f'{n_eruptions:,} eruptions at {n_volcanoes:,} volcanoes',
        xy=(0.02, 0.02),
        xycoords='axes fraction',
        fontsize=9,
        color='#555555'
    )
    
    # Add source annotation
    ax.annotate(
        'Data: NOAA NGDC Significant Volcanic Eruptions Database',
        xy=(0.98, 0.02),
        xycoords='axes fraction',
        fontsize=8,
        color='#888888',
        ha='right'
    )
    
    plt.tight_layout()
    
    # Save figure
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
    print(f"Map saved to {output_path}")
    
    return fig, ax


def main():
    # Paths (script is in src folder, data is in data folder)
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    data_path = repo_root / 'data' / 'volcano_list.csv'
    output_path = repo_root / 'results' / 'figures' / 'holocene_volcanic_eruptions.png'
    
    # Verify data file exists
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    # Load data
    print("Loading volcano data...")
    df = load_volcano_data(data_path)
    print(f"Loaded {len(df)} eruptions with valid coordinates and VEI")
    
    # Print VEI distribution
    print("\nVEI distribution:")
    vei_counts = df['VEI'].value_counts().sort_index()
    for vei, count in vei_counts.items():
        print(f"  VEI {vei}: {count} eruptions")
    
    # Convert to GeoDataFrame
    volcano_gdf = create_volcano_geodataframe(df)
    
    # Create map
    print("\nCreating map...")
    fig, ax = plot_volcano_map(volcano_gdf, output_path)
    
    plt.show()


if __name__ == '__main__':
    main()