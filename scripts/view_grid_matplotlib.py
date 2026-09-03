#!/usr/bin/env python3
"""View the IEEE 39-bus power grid using GeoJSON + matplotlib + OSM tiles."""

import argparse
import json
import os
import sys
from pathlib import Path

import geojson
import matplotlib.pyplot as plt

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from geojson import Feature, FeatureCollection

from epowcore.gdf.bus import Bus
from epowcore.gdf.core_model import CoreModel

# IEEE 39-bus coordinates (New England)
BUS_COORDS = {
    0: (42.36, -71.06),
    1: (42.05, -70.75),
    2: (41.82, -70.45),
    3: (41.70, -70.10),
    4: (41.55, -69.75),
    5: (41.40, -69.40),
    6: (41.25, -69.05),
    7: (41.10, -68.70),
    8: (40.95, -68.35),
    9: (42.30, -71.40),
    10: (42.25, -71.50),
    11: (42.20, -71.60),
    12: (42.15, -71.70),
    13: (42.10, -71.80),
    14: (42.05, -71.90),
    15: (42.00, -72.00),
    16: (41.95, -72.10),
    17: (41.90, -72.20),
    18: (41.85, -72.30),
    19: (41.80, -72.40),
    20: (41.75, -72.50),
    21: (41.70, -72.60),
    22: (41.65, -72.70),
    23: (41.60, -72.80),
    24: (41.55, -72.90),
    25: (41.50, -73.00),
    26: (41.45, -73.10),
    27: (41.40, -73.20),
    28: (41.35, -73.30),
    29: (41.95, -71.00),
    30: (41.90, -70.85),
    31: (41.85, -70.70),
    32: (41.80, -70.55),
    33: (41.75, -70.40),
    34: (41.70, -70.25),
    35: (41.65, -70.10),
    36: (41.60, -69.95),
    37: (41.55, -69.80),
    38: (42.10, -71.05),
}
COLORS = {
    "Bus": "#2E86AB",
    "Generator": "#28A745",
    "Load": "#DC3545",
    "Transformer": "#FFC107",
}


def color(t):
    return COLORS.get(t, "#17A2B8")


def model_to_geojson(model: CoreModel) -> dict:
    """Convert CoreModel to GeoJSON (mirrors the project's converter)."""
    features = []
    for node in model.graph.nodes:
        if node.coords is not None and node.coords:
            props = {"uid": node.uid, "name": node.name, "type": type(node).__name__}
            if isinstance(node.coords, tuple):
                # Point: GeoJSON uses (lon, lat)
                features.append(
                    Feature(
                        id=node.uid,
                        geometry={
                            "type": "Point",
                            "coordinates": (node.coords[1], node.coords[0]),
                        },
                        properties=props,
                    )
                )
            else:
                # LineString
                coords = [(c[1], c[0]) for c in node.coords]
                features.append(
                    Feature(
                        id=node.uid,
                        geometry={"type": "LineString", "coordinates": coords},
                        properties=props,
                    )
                )
    return FeatureCollection(features)


def main():
    ap = argparse.ArgumentParser(
        description="GeoJSON + matplotlib + OSM for IEEE 39-bus"
    )
    ap.add_argument("--save", action="store_true", help="Save PNG")
    ap.add_argument("--no-tiles", action="store_true", help="No OSM background")
    ap.add_argument(
        "--style", default="default", choices=["default", "satellite", "dark", "topo"]
    )
    ap.add_argument("--export-json", type=str, help="Save GeoJSON")
    args = ap.parse_args()

    # Load model
    p = Path(project_root) / "neuthard_gdf.json"
    print(f"Loading: {p}")
    with open(p) as f:
        model = CoreModel.import_dict(json.load(f))
    print(f"  -> {len(model.graph.nodes)} nodes, {len(model.graph.edges)} edges")

    # Add coordinates
    for b in model.type_list(Bus):
        if b.uid in BUS_COORDS:
            b.coords = BUS_COORDS[b.uid]
    for c in model.graph.nodes:
        if c.coords is None:
            for nb in model.graph.neighbors(c):
                if isinstance(nb, Bus) and nb.coords:
                    lat, lon = nb.coords
                    ct = type(c).__name__
                    c.coords = (
                        lat + 0.002
                        if "Transformer" in ct
                        else lat - 0.001
                        if "Generator" in ct
                        else lat + 0.001,
                        lon + 0.002
                        if "Transformer" in ct
                        else lon - 0.001
                        if "Generator" in ct
                        else lon + 0.001,
                    )
                    break

    # Export GeoJSON
    print("Exporting to GeoJSON...")
    data = model_to_geojson(model)
    print(f"  -> {len(data['features'])} features")

    if args.export_json:
        out = Path(project_root) / "output" / args.export_json
        out.parent.mkdir(exist_ok=True)
        with open(out, "w") as f:
            geojson.dump(data, f, indent=2)
        print(f"GeoJSON saved: {out}")

    # Plot
    import contextily as ctx

    pts, lines = [], []
    for f in data["features"]:
        g, props = f.get("geometry", {}), f.get("properties", {})
        if g.get("type") == "Point":
            pts.append(
                {
                    "c": (g["coordinates"][1], g["coordinates"][0]),
                    "t": props.get("type", "Unknown"),
                }
            )
        elif g.get("type") == "LineString":
            lines.append([(c[1], c[0]) for c in g["coordinates"]])

    fig, ax = plt.subplots(figsize=(14, 10))
    for l in lines:
        ax.plot(
            [x[1] for x in l],
            [x[0] for x in l],
            color="#555",
            lw=1.5,
            alpha=0.7,
            zorder=1,
        )
    for p in pts:
        ax.scatter(
            p["c"][1],
            p["c"][0],
            c=color(p["t"]),
            s=100,
            ec="white",
            zorder=2,
            alpha=0.9,
        )

    if not args.no_tiles:
        try:
            provs = {
                "default": ctx.providers.OpenStreetMap.Mapnik,
                "satellite": ctx.providers.Esri.WorldImagery,
                "dark": ctx.providers.CartoDB.DarkMatter,
                "topo": ctx.providers.OpenTopoMap,
            }
            ctx.add_basemap(ax, crs="EPSG:4326", source=provs[args.style])
            print(f"OSM tiles: {args.style}")
        except Exception as e:
            print(f"Tile error: {e}")

    h = [plt.scatter([], [], c=c, s=100, label=k) for k, c in COLORS.items()]
    ax.legend(h, COLORS.keys(), title="Type", loc="lower right", fontsize=9)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("IEEE 39-Bus Grid", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, ls="--")
    plt.tight_layout()

    if args.save:
        out = Path(project_root) / "output" / "ieee39_matplotlib.png"
        out.parent.mkdir(exist_ok=True)
        fig.savefig(out, dpi=150, facecolor="white")
        print(f"Saved: {out}")
    else:
        print("Displaying...")
        plt.show()
    plt.close(fig)


if __name__ == "__main__":
    main()
