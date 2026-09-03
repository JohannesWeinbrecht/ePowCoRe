#!/usr/bin/env python3
"""View the IEEE 39-bus power grid in your browser.

Usage:
    python view_grid.py --graph      Show only the interactive network graph
    python view_grid.py --map        Show only the OSM map
    python view_grid.py --names      Display component names
    python view_grid.py --types      Color by component type
    python view_grid.py --export     Save visualizations to files
    python view_grid.py              Show both visualizations (default)
"""

import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from epowcore.gdf.core_model import CoreModel
from epowcore.gdf.bus import Bus

# Approximate coordinates for IEEE 39-bus (New England area)
BUS_COORDINATES = {
    0: (42.3601, -71.0589), 1: (42.05, -70.75), 2: (41.82, -70.45),
    3: (41.70, -70.10), 4: (41.55, -69.75), 5: (41.40, -69.40),
    6: (41.25, -69.05), 7: (41.10, -68.70), 8: (40.95, -68.35),
    9: (42.30, -71.40), 10: (42.25, -71.50), 11: (42.20, -71.60),
    12: (42.15, -71.70), 13: (42.10, -71.80), 14: (42.05, -71.90),
    15: (42.00, -72.00), 16: (41.95, -72.10), 17: (41.90, -72.20),
    18: (41.85, -72.30), 19: (41.80, -72.40), 20: (41.75, -72.50),
    21: (41.70, -72.60), 22: (41.65, -72.70), 23: (41.60, -72.80),
    24: (41.55, -72.90), 25: (41.50, -73.00), 26: (41.45, -73.10),
    27: (41.40, -73.20), 28: (41.35, -73.30), 29: (41.95, -71.00),
    30: (41.90, -70.85), 31: (41.85, -70.70), 32: (41.80, -70.55),
    33: (41.75, -70.40), 34: (41.70, -70.25), 35: (41.65, -70.10),
    36: (41.60, -69.95), 37: (41.55, -69.80), 38: (42.10, -71.05),
}


def load_model(json_path: str) -> CoreModel:
    print(f"Loading: {json_path}")
    with open(json_path) as f:
        data = json.load(f)
    model = CoreModel.import_dict(data)
    print(f"  -> {len(model.graph.nodes)} components, {len(model.graph.edges)} connections")
    return model


def add_coords(model: CoreModel) -> CoreModel:
    for bus in model.type_list(Bus):
        if bus.uid in BUS_COORDINATES:
            bus.coords = BUS_COORDINATES[bus.uid]
    for comp in model.graph.nodes:
        if comp.coords is None:
            for neighbor in model.graph.neighbors(comp):
                if isinstance(neighbor, Bus) and neighbor.coords:
                    lat, lon = neighbor.coords
                    comp_type = type(comp).__name__
                    if "Transformer" in comp_type:
                        comp.coords = (lat + 0.002, lon + 0.002)
                    elif "Generator" in comp_type:
                        comp.coords = (lat - 0.001, lon - 0.001)
                    else:
                        comp.coords = (lat + 0.001, lon + 0.001)
                    break
    return model


def open_in_browser(html: str, filename: str):
    output_dir = Path(project_root) / "output"
    output_dir.mkdir(exist_ok=True)
    path = output_dir / filename
    path.write_text(html, encoding='utf-8')
    print(f"\nOpening in browser: {path}")
    webbrowser.open(f"file://{path.resolve()}")


def show_graph(model: CoreModel, names: bool, types: bool, export: str | None):
    print("\n[Interactive Network Graph - Plotly]")
    try:
        html = model.plot_interactive_graph(show_names=names, show_types=types, export_path=export)
        if export:
            print(f"Saved: {export}")
        else:
            open_in_browser(html, "temp_interactive_graph.html")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def show_map(model: CoreModel, names: bool, types: bool, export: str | None, zoom: int):
    print("\n[Geographic Map - OpenStreetMap]")
    try:
        html = model.plot_osm_map(show_names=names, show_types=types, export_path=export, zoom_start=zoom)
        if export:
            print(f"Saved: {export}")
        else:
            open_in_browser(html, "temp_osm_map.html")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="View the IEEE 39-bus power grid")
    parser.add_argument("--graph", action="store_true", help="Show only the network graph")
    parser.add_argument("--map", action="store_true", help="Show only the OSM map")
    parser.add_argument("--names", action="store_true", help="Display component names")
    parser.add_argument("--types", action="store_true", help="Color by component type")
    parser.add_argument("--export", action="store_true", help="Save visualizations to files")
    parser.add_argument("--zoom", type=int, default=8, help="Map zoom level (default: 8)")
    parser.add_argument("--json", type=str, default=None, help="Path to JSON model file")
    args = parser.parse_args()

    show_graph_only = args.graph
    show_map_only = args.map

    json_path = args.json or str(Path(project_root) / "tests" / "models" / "gdf" / "IEEE39_gdf.json")
    if not Path(json_path).exists():
        print(f"Error: Model file not found: {json_path}")
        sys.exit(1)

    print("=" * 50)
    print("IEEE 39-BUS POWER GRID VISUALIZATION")
    print("=" * 50)

    model = load_model(json_path)

    if not show_graph_only:
        print("Adding geographic coordinates...")
        model = add_coords(model)

    export_dir = Path(project_root) / "output"
    export_dir.mkdir(exist_ok=True)

    if not show_map_only:
        path = str(export_dir / "ieee39_graph.html") if args.export else None
        show_graph(model, names=args.names, types=args.types, export=path)

    if not show_graph_only:
        path = str(export_dir / "ieee39_map.html") if args.export else None
        show_map(model, names=args.names, types=args.types, export=path, zoom=args.zoom)

    if args.export:
        print(f"\nFiles saved to: {export_dir}")


if __name__ == "__main__":
    main()