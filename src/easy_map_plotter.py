"""
ALLFED-style global map creator with easy country grouping.

Usage:
    from allfed_map import WorldMap

    # Define country groups as {group_name: (list_of_countries, color, label)}
    groups = {
        'high_risk': (['USA', 'China', 'India'], '#d62728', 'High Risk'),
        'medium_risk': (['Brazil', 'Russia'], '#ff7f0e', 'Medium Risk'),
    }

    wm = WorldMap()
    fig, ax = wm.plot(groups)
    plt.show()
"""

import matplotlib.pyplot as plt
import geopandas as gpd
import warnings

# Apply ALLFED style
plt.style.use(
    "https://raw.githubusercontent.com/allfed/ALLFED-matplotlib-style-sheet/main/ALLFED.mplstyle"
)


def load_world_data():
    """Load Natural Earth country boundaries."""
    # The old gpd.datasets method is deprecated; use the online source directly
    url = (
        "https://naciscdn.org/naturalearth/110m/cultural/ne_110m_admin_0_countries.zip"
    )
    try:
        world = gpd.read_file(url)
    except Exception:
        # Fallback to legacy method if available
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            world = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
    return world


def load_border():
    """Load ALLFED map border."""
    url = (
        "https://raw.githubusercontent.com/ALLFED/ALLFED-map-border/main/border.geojson"
    )
    border = gpd.read_file(url)
    # The file is mislabeled - coordinates are already in Winkel Tripel, not WGS84
    border = border.set_crs("+proj=wintri", allow_override=True)
    return border


class WorldMap:
    """
    Create ALLFED-style world maps with grouped country highlighting.

    Parameters
    ----------
    default_color : str
        Color for countries not in any group. Default: light gray.
    ocean_color : str
        Background color (ocean). Default: white.
    border_color : str
        Color for country borders. Default: dark gray.
    """

    def __init__(
        self, default_color="#F5F5F5", ocean_color="white", border_color="#404040"
    ):
        self.default_color = default_color
        self.ocean_color = ocean_color
        self.border_color = border_color
        self.world = load_world_data()
        self.border = load_border()

        # Reproject world data to Winkel Tripel
        self.world = self.world.to_crs("+proj=wintri")
        # Border is already in Winkel Tripel (no reprojection needed)

    def _match_countries(self, country_list):
        """
        Match country names/codes to the dataset.
        Accepts: ISO A3 codes, ISO A2 codes, or country names.
        """
        matched = self.world[
            self.world["NAME"].isin(country_list)
            | self.world["ISO_A3"].isin(country_list)
            | self.world["ISO_A2"].isin(country_list)
        ]

        # Warn about unmatched countries
        all_matched = (
            set(matched["NAME"]) | set(matched["ISO_A3"]) | set(matched["ISO_A2"])
        )
        unmatched = [c for c in country_list if c not in all_matched]
        if unmatched:
            warnings.warn(f"Could not match countries: {unmatched}")

        return matched.index

    def plot(self, groups=None, figsize=(12, 7), title=None, show_legend=True):
        """
        Plot the world map with highlighted country groups.

        Parameters
        ----------
        groups : dict
            Dictionary mapping group names to tuples of:
            (list_of_countries, color, label)

            Example:
            {
                'exporters': (['USA', 'CAN', 'AUS'], '#2ca02c', 'Major Exporters'),
                'importers': (['JPN', 'GBR'], '#d62728', 'Net Importers'),
            }

            Countries can be specified by name ('United States of America'),
            ISO A3 code ('USA'), or ISO A2 code ('US').

        figsize : tuple
            Figure size in inches.
        title : str
            Optional title for the map.
        show_legend : bool
            Whether to show the legend.

        Returns
        -------
        fig, ax : matplotlib figure and axes
        """
        groups = groups or {}

        # Create color column
        self.world["_color"] = self.default_color

        # Apply group colors
        legend_handles = []
        for group_name, (countries, color, label) in groups.items():
            idx = self._match_countries(countries)
            self.world.loc[idx, "_color"] = color

            # Create legend handle
            handle = plt.Rectangle(
                (0, 0), 1, 1, facecolor=color, edgecolor="none", label=label
            )
            legend_handles.append(handle)

        # Create figure
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_facecolor(self.ocean_color)

        # Plot countries
        self.world.plot(
            ax=ax,
            color=self.world["_color"],
            edgecolor=self.border_color,
            linewidth=0.3,
        )

        # Add ALLFED border (zorder ensures it's drawn on top)
        self.border.plot(ax=ax, edgecolor="black", linewidth=0.5, facecolor="none")

        # Clean up axes
        ax.set_axis_off()

        # Add title
        if title:
            ax.set_title(title, fontsize=14, pad=10)

        # Add legend
        if show_legend and legend_handles:
            ax.legend(
                handles=legend_handles, loc="lower left", frameon=True, framealpha=0.9
            )

        plt.tight_layout()
        return fig, ax


# Convenience function for quick plots
def quick_map(groups, title=None, figsize=(12, 7)):
    """
    Quick way to create a map without instantiating WorldMap.

    Example:
        quick_map({
            'group1': (['USA', 'CAN'], 'green', 'North America'),
            'group2': (['DEU', 'FRA'], 'blue', 'Europe'),
        })
    """
    wm = WorldMap()
    return wm.plot(groups, figsize=figsize, title=title)


if __name__ == "__main__":
    # Country resilience to global catastrophic risks
    # ASRS: Abrupt Sunlight Reduction Scenarios (nuclear winter, volcanic winter, asteroid)
    # GCIL: Global Catastrophic Infrastructure Loss (EMP, geomagnetic storms)
    # GCBR: Global Catastrophic Biological Risks (pandemics)

    asrs = {"Australia", "New Zealand", "Argentina", "Brazil", "Uruguay", "Chile"}
    gcil = {"Australia", "New Zealand", "Switzerland", "Uruguay", "China", "Brazil"}
    gcbr = {
        "Australia",
        "New Zealand",
        "Norway",
        "Sweden",
        "Denmark",
        "Finland",
        "Canada",
        "Switzerland",
        "Japan",
        "KOR",
    }  # KOR = South Korea ISO code

    # Compute exclusive categories
    all_three = asrs & gcil & gcbr
    gcil_asrs = (gcil & asrs) - gcbr
    gcil_gcbr = (gcil & gcbr) - asrs
    asrs_gcbr = (asrs & gcbr) - gcil  # Empty in this dataset
    asrs_only = asrs - gcil - gcbr
    gcil_only = gcil - asrs - gcbr
    gcbr_only = gcbr - asrs - gcil

    # Build groups dict, skipping empty sets
    groups = {}

    if all_three:
        groups["all_three"] = (list(all_three), "#779d77", "All Considered Risks")
    if gcil_asrs:
        groups["gcil_asrs"] = (
            list(gcil_asrs),
            "#bca97b",
            "Loss of Sunlight and Infrastructure",
        )
    if gcil_gcbr:
        groups["gcil_gcbr"] = (
            list(gcil_gcbr),
            "#ac6b7e",
            "Biological Risks and Loss of Infrastructure",
        )
    if asrs_gcbr:
        groups["asrs_gcbr"] = (
            list(asrs_gcbr),
            "#8d796d",
            "Biological Risks and Loss of Sunlight",
        )
    if asrs_only:
        groups["asrs_only"] = (list(asrs_only), "#779cae", "Loss of Sunlight only")
    if gcil_only:
        groups["gcil_only"] = (
            list(gcil_only),
            "#b58365",
            "Loss of Infrastructure only",
        )
    if gcbr_only:
        groups["gcbr_only"] = (list(gcbr_only), "#8c798c", "Biological Risks only")

    wm = WorldMap()
    fig, ax = wm.plot(groups, title="Resilience to Global Catastrophic Risks")
    plt.savefig("results/figures/gcr_resilience_map.png", dpi=150, bbox_inches="tight")
    plt.show()

    # Nuclear weapon states
    nuclear_states = {
        "USA",
        "Russia",
        "United Kingdom",
        "France",
        "China",
        "India",
        "Pakistan",
        "North Korea",
        "Israel",
    }

    # NATO members (32)
    nato = {
        "Albania",
        "Belgium",
        "Bulgaria",
        "Canada",
        "Croatia",
        "Czech Republic",
        "Denmark",
        "Estonia",
        "Finland",
        "France",
        "Germany",
        "Greece",
        "Hungary",
        "Iceland",
        "Italy",
        "Latvia",
        "Lithuania",
        "Luxembourg",
        "Montenegro",
        "Netherlands",
        "North Macedonia",
        "Norway",
        "Poland",
        "Portugal",
        "Romania",
        "Slovakia",
        "Slovenia",
        "Spain",
        "Sweden",
        "Turkey",
        "United Kingdom",
        "USA",
    }

    # CSTO members
    csto = {"Armenia", "Belarus", "Kazakhstan", "Kyrgyzstan", "Russia", "Tajikistan"}

    # Non-NATO US allies with nuclear umbrella
    us_allies_asia = {"Japan", "South Korea", "Australia"}

    # China-North Korea defense pact
    china_nk = {"China", "North Korea"}

    # Pakistan-Saudi Arabia defense pact
    pakistan_saudi = {"Pakistan", "Saudi Arabia"}

    # Independent nuclear states (not in major alliances)
    independent_nuclear = (
        nuclear_states - nato - csto - us_allies_asia - china_nk - pakistan_saudi
    )
    # This gives us: India, Israel

    # Build the map with ordered groups (later groups override earlier ones)
    groups = {}

    # Start with NATO (medium blue, not too bright)
    groups["nato"] = (
        list(nato),
        "#5B88A8",
        "NATO (includes US, UK, France with nuclear weapons)",
    )

    # CSTO (muted red) - will override for countries in both
    groups["csto"] = (
        list(csto),
        "#A85858",
        "CSTO (includes Russia with nuclear weapons)",
    )

    # Non-NATO US allies (lighter blue)
    groups["us_allies"] = (
        list(us_allies_asia),
        "#8FADBD",
        "US allies with nuclear umbrella",
    )

    # China-North Korea defense pact (muted purple-grey)
    groups["china_nk"] = (
        list(china_nk),
        "#8B7B8A",
        "China-North Korea defense pact, both with nuclear weapons",
    )

    # Pakistan-Saudi Arabia defense pact (muted olive-green)
    groups["pakistan_saudi"] = (
        list(pakistan_saudi),
        "#8B9B7A",
        "Pakistan-Saudi Arabia defense pact, Pakistan with nuclear weapons",
    )

    # Independent nuclear states (muted orange-tan)
    groups["independent_nuclear"] = (
        list(independent_nuclear),
        "#B08860",
        "Nuclear weapon states without mutual defense agreements",
    )

    wm = WorldMap()
    fig, ax = wm.plot(groups, title="Nuclear Weapon States and Alliances")
    plt.savefig(
        "results/figures/nuclear_alliances_map.png", dpi=150, bbox_inches="tight"
    )
    print("Map saved to nuclear_alliances_map.png")
    plt.show()
