"""
ALLFED-style global map creator with easy country grouping.

Creates:
    Figure 1: Three stacked world maps (ASRS, GCIL, GCBR)
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
    """Load ALLFED map border."""
    url = (
        "https://raw.githubusercontent.com/ALLFED/ALLFED-map-border/main/border.geojson"
    )
    border = gpd.read_file(url)
    border = border.set_crs("+proj=wintri", allow_override=True)
    return border


class WorldMap:
    """Create ALLFED-style world maps with grouped country highlighting."""

    def __init__(
        self, default_color="#F5F5F5", ocean_color="white", border_color="#404040"
    ):
        self.default_color = default_color
        self.ocean_color = ocean_color
        self.border_color = border_color
        self.world = load_world_data()
        self.border = load_border()
        self.world = self.world.to_crs("+proj=wintri")

    def _match_countries(self, country_list):
        """Match country names/codes to the dataset."""
        matched = self.world[
            self.world["NAME"].isin(country_list)
            | self.world["ISO_A3"].isin(country_list)
            | self.world["ISO_A2"].isin(country_list)
        ]

        all_matched = (
            set(matched["NAME"]) | set(matched["ISO_A3"]) | set(matched["ISO_A2"])
        )
        unmatched = [c for c in country_list if c not in all_matched]
        if unmatched:
            warnings.warn(f"Could not match countries: {unmatched}")

        return matched.index

    def plot_single(self, ax, countries, color):
        """
        Plot a single map on a given axes.

        Parameters
        ----------
        ax : matplotlib axes
            The axes to plot on.
        countries : set or list
            Countries to highlight.
        color : str
            Color for highlighted countries.
        """
        colors = [self.default_color] * len(self.world)

        idx = self._match_countries(countries)
        for i in idx:
            colors[i] = color

        ax.set_facecolor(self.ocean_color)

        self.world.plot(ax=ax, color=colors, edgecolor=self.border_color, linewidth=0.3)

        self.border.plot(ax=ax, edgecolor="black", linewidth=0.5, facecolor="none")
        ax.set_axis_off()

    def plot_stacked(self, categories, figsize=(10, 14)):
        """
        Plot multiple maps stacked vertically with titles above each map.

        Parameters
        ----------
        categories : list of tuples
            Each tuple: (countries_set, color, title)
        figsize : tuple
            Figure size in inches.

        Returns
        -------
        fig, axes
        """
        n = len(categories)

        fig, axes = plt.subplots(n, 1, figsize=figsize)

        if n == 1:
            axes = [axes]

        for ax, (countries, color, title) in zip(axes, categories):
            self.plot_single(ax, countries, color)
            ax.set_title(title, fontsize=11, pad=5)

        plt.tight_layout()
        return fig, axes


if __name__ == "__main__":
    # Define country sets
    asrs = {"Australia", "New Zealand", "Argentina", "Brazil", "Uruguay", "Chile"}
    gcil = {"Australia", "New Zealand", "Switzerland", "Uruguay", "China", "Brazil", "Cuba"}
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
    }

    # Figure 1: Three stacked maps
    wm = WorldMap()

    categories = [
        (asrs, "#779d77", "ASRS: Abrupt Sunlight Reduction Scenarios"),
        (gcil, "#b58365", "GCIL: Global Catastrophic Infrastructure Loss"),
        (gcbr, "#8c798c", "GCBR: Global Catastrophic Biological Risks"),
    ]

    fig, axes = wm.plot_stacked(categories)
    fig.savefig(
        "results/figures/gcr_resilience_stacked_maps.png", dpi=150, bbox_inches="tight"
    )

    plt.show()
