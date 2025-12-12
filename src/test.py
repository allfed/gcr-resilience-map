import geopandas as gpd

url = 'https://raw.githubusercontent.com/ALLFED/ALLFED-map-border/main/border.geojson'
border = gpd.read_file(url)

print("CRS as loaded:", border.crs)
print("Bounds as loaded:", border.total_bounds)
print("Geometry validity:", border.is_valid.all())
print("First geometry:", border.geometry.iloc[0])