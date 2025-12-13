import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pathlib import Path
import warnings

# Set up paths
project_root = Path(__file__).parent.parent
data_path = project_root / "data" / "2021-GHS-Index-April-2022.csv"
output_path = project_root / "results" / "figures"
output_path.mkdir(parents=True, exist_ok=True)

# Load ALLFED plotting style
plt.style.use("https://raw.githubusercontent.com/allfed/ALLFED-matplotlib-style-sheet/main/ALLFED.mplstyle")

def load_world_data():
    """Load Natural Earth country boundaries."""
    # The old gpd.datasets method is deprecated; use the online source directly
    url = "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
    try:
        world = gpd.read_file(url)
    except Exception:
        # Fallback to legacy method if available
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
    return world

def plot_winkel_tripel_map(ax):
    """Modify style for maps and add border."""
    border_geojson = gpd.read_file('https://raw.githubusercontent.com/ALLFED/ALLFED-map-border/main/border.geojson')
    border_geojson.plot(ax=ax, edgecolor='black', linewidth=0.1, facecolor='none')
    ax.set_axis_off()

# Load data
ghs_data = pd.read_csv(data_path)
world = load_world_data()

# Comprehensive country name mapping from Natural Earth to GHS Index
name_mapping = {
    # Congos
    'Democratic Republic of the Congo': 'Congo (Democratic Republic)',
    'Republic of the Congo': 'Congo (Brazzaville)',
    # Major countries
    'United States of America': 'United States of America',
    'Russian Federation': 'Russia',
    'China': 'China',
    # Tanzania
    'United Republic of Tanzania': 'Tanzania',
    # Bahamas
    'The Bahamas': 'Bahamas',
    # Serbia
    'Republic of Serbia': 'Serbia',
    # Ivory Coast - Natural Earth uses "Ivory Coast", not the French name
    'Ivory Coast': 'Côte d\'Ivoire',
    # Gambia
    'The Gambia': 'Gambia',
    # Bosnia
    'Bosnia and Herzegovina': 'Bosnia and Hercegovina',
    # Korea
    'Republic of Korea': 'South Korea',
    "Democratic People's Republic of Korea": 'North Korea',
    # Kosovo - use Serbia's data
    'Kosovo': 'Serbia',
    # Western Sahara - use Morocco's data
    'Western Sahara': 'Morocco',
    # Other common mismatches
    'Kyrgyzstan': 'Kyrgyz Republic',
    'Equatorial Guinea': 'Equatorial Guinea',
    'Somaliland': 'Somalia',
    'Czechia': 'Czech Republic',
    'Czech Republic': 'Czech Republic',
    'North Macedonia': 'North Macedonia',
    'Macedonia': 'North Macedonia',
    'Northern Cyprus': 'Cyprus',
    'Lao PDR': 'Laos',
    'Brunei': 'Brunei',
    'Brunei Darussalam': 'Brunei',
    'Myanmar': 'Myanmar',
    'Burma': 'Myanmar',
    'Timor-Leste': 'Timor-Leste',
    'East Timor': 'Timor-Leste',
    'Swaziland': 'eSwatini',
}

# Use ADMIN column which has full administrative names in English
country_col = 'ADMIN' if 'ADMIN' in world.columns else 'NAME'

# Create a mapped name column for matching
world['country_match'] = world[country_col].replace(name_mapping)

# Merge GHS data with world geometries
world_ghs = world.merge(ghs_data, left_on='country_match', right_on='Country', how='left')

# Check for unmatched countries (excluding territories that aren't in GHS dataset)
unmatched_world = world_ghs[world_ghs['OVERALL SCORE'].isna()][country_col].unique()
territories_not_in_ghs = ['Greenland', 'Falkland Islands', 'French Southern and Antarctic Lands', 
                          'Puerto Rico', 'New Caledonia', 'Antarctica', 'Taiwan', 'Palestine']
unmatched_countries = [c for c in unmatched_world if c not in territories_not_in_ghs]

if len(unmatched_countries) > 0:
    print(f"Countries in map but not matched to GHS data: {len(unmatched_countries)}")
    print(unmatched_countries[:30])

# Project to Winkel Tripel
world_ghs = world_ghs.to_crs('+proj=wintri')

# Create the plot
fig, ax = plt.subplots(figsize=(14, 8))

world_ghs.plot(
    column='OVERALL SCORE',
    ax=ax,
    cmap='cividis_r',
    vmin=0, vmax=100,
    legend=True,
    missing_kwds={'color': 'lightgrey'},
    edgecolor='white',
    linewidth=0.3,
    legend_kwds={
        'label': 'Global Health Security Index Score',
        'orientation': 'horizontal',
        'shrink': 0.3,
        'pad': 0.05
    }
)

plot_winkel_tripel_map(ax)

plt.title('Global Health Security Index 2021', fontsize=14, pad=20)
plt.figtext(0.5, 0.02, 'Source: Global Health Security Index 2021', 
            ha='center', fontsize=9, style='italic')

# Save figure
plt.tight_layout()
plt.savefig(output_path / 'global_health_security_index_map.png', 
            dpi=300, bbox_inches='tight')
print(f"Map saved to {output_path / 'global_health_security_index_map.png'}")

plt.close()