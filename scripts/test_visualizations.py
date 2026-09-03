#!/usr/bin/env python3
"""Test script for interactive visualization methods on the IEEE 39-bus model.

This script demonstrates the two new visualization methods:
- plot_interactive_graph(): Interactive network graph using Plotly
- plot_osm_map(): Geographic network plot on OpenStreetMap using Folium

Usage:
    python test_visualizations.py [options]

Options:
    --interactive      Test only the interactive graph
    --osm            Test only the OSM map
    --names           Enable name labels in visualizations
    --types           Enable component type coloring in visualizations
    --export          Save visualizations to files
    --all             Run all tests with all options enabled
"""

import argparse
import json
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from epowcore.gdf.core_model import CoreModel


def load_ieee39_model(json_path: str) -> CoreModel:
    """Load the IEEE 39-bus model from a JSON file."""
    print(f"Loading model from: {json_path}")
    with open(json_path, "r") as f:
        data = json.load(f)
    model = CoreModel.import_dict(data)
    print(f"  Loaded {len(model.graph.nodes)} components and {len(model.graph.edges)} connections")
    return model


def add_coordinates_to_model(model: CoreModel) -> CoreModel:
    """Add geographic coordinates to model components for OSM visualization."""
    from epowcore.gdf.bus import Bus
    
    # Approximate coordinates for IEEE 39-bus test system
    bus_coordinates = {
        0: (42.3601, -71.0589), 1: (42.0500, -70.7500), 2: (41.8200, -70.4500),
        3: (41.7000, -70.1000), 4: (41.5500, -69.7500), 5: (41.4000, -69.4000),
        6: (41.2500, -69.0500), 7: (41.1000, -68.7000), 8: (40.9500, -68.3500),
        9: (42.3000, -71.4000), 10: (42.2500, -71.5000), 11: (42.2000, -71.6000),
        12: (42.1500, -71.7000), 13: (42.1000, -71.8000), 14: (42.0500, -71.9000),
        15: (42.0000, -72.0000), 16: (41.9500, -72.1000), 17: (41.9000, -72.2000),
        18: (41.8500, -72.3000), 19: (41.8000, -72.4000), 20: (41.7500, -72.5000),
        21: (41.7000, -72.6000), 22: (41.6500, -72.7000), 23: (41.6000, -72.8000),
        24: (41.5500, -72.9000), 25: (41.5000, -73.0000), 26: (41.4500, -73.1000),
        27: (41.4000, -73.2000), 28: (41.3500, -73.3000), 29: (41.9500, -71.0000),
        30: (41.9000, -70.8500), 31: (41.8500, -70.7000), 32: (41.8000, -70.5500),
        33: (41.7500, -70.4000), 34: (41.7000, -70.2500), 35: (41.6500, -70.1000),
        36: (41.6000, -69.9500), 37: (41.5500, -69.8000), 38: (42.1000, -71.0500),
    }
    
    for bus in model.type_list(Bus):
        if bus.uid in bus_coordinates:
            lat, lon = bus_coordinates[bus.uid]
            bus.coords = (lat, lon)
    
    for component in model.graph.nodes:
        if component.coords is None:
            for neighbor in model.graph.neighbors(component):
                if isinstance(neighbor, Bus) and neighbor.coords is not None:
                    lat, lon = neighbor.coords
                    if "Transformer" in type(component).__name__:
                        component.coords = (lat + 0.001, lon + 0.001)
                    elif "Generator" in type(component).__name__:
                        component.coords = (lat - 0.001, lon - 0.001)
                    else:
                        component.coords = (lat + 0.0005, lon + 0.0005)
                    break
    
    return model


def test_interactive_graph(model: CoreModel, show_names: bool = False,
    show_types: bool = False, export_path: str | None = None) -> str | None:
    """Test the interactive graph visualization."""
    print(f"\n=== Interactive Network Graph ===")
    print(f"  show_names={show_names}, show_types={show_types}")
    
    try:
        result = model.plot_interactive_graph(
            show_names=show_names, show_types=show_types, export_path=export_path)
        
        if export_path:
            print(f"  SUCCESS: Saved to {export_path}")
            return None
        else:
            print(f"  SUCCESS: Generated HTML ({len(result) if result else 0:,} chars)")
            return result
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_osm_map(model: CoreModel, show_names: bool = False,
    show_types: bool = False, export_path: str | None = None,
    zoom_start: int = 10) -> str | None:
    """Test the OSM map visualization."""
    print(f"\n=== OpenStreetMap Visualization ===")
    print(f"  show_names={show_names}, show_types={show_types}, zoom={zoom_start}")
    
    try:
        result = model.plot_osm_map(
            show_names=show_names, show_types=show_types,
            export_path=export_path, zoom_start=zoom_start)
        
        if export_path:
            print(f"  SUCCESS: Saved to {export_path}")
            return None
        else:
            print(f"  SUCCESS: Generated HTML ({len(result) if result else 0:,} chars)")
            return result
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    parser = argparse.ArgumentParser(
        description="Test interactive visualizations on the IEEE 39-bus model")
    parser.add_argument("--json", type=str, default=None,
        help="Path to JSON model file")
    parser.add_argument("--interactive", action="store_true",
        help="Test only the interactive graph")
    parser.add_argument("--osm", action="store_true",
        help="Test only the OSM map")
    parser.add_argument("--names", action="store_true",
        help="Enable component name labels")
    parser.add_argument("--types", action="store_true",
        help="Enable component type coloring")
    parser.add_argument("--export", action="store_true",
        help="Export visualizations to files")
    parser.add_argument("--all", action="store_true",
        help="Run all tests with all options")
    parser.add_argument("--no-coords", action="store_true",
        help="Test without adding coordinates")
    parser.add_argument("--zoom", type=int, default=8,
        help="Initial zoom level for OSM map (1-18, default: 8)")
    
    args = parser.parse_args()
    
    # Determine test modes
    test_interactive = args.interactive or not args.osm
    test_osm = args.osm or not args.interactive
    
    if args.all:
        test_interactive = True
        test_osm = True
        args.names = True
        args.types = True
        args.export = True
    
    # Determine JSON path
    if args.json:
        json_path = args.json
    else:
        json_path = os.path.join(project_root, "tests", "models", "gdf", "IEEE39_gdf.json")
    
    if not os.path.exists(json_path):
        print(f"ERROR: JSON file not found: {json_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("Loading IEEE 39-Bus Test System Model")
    print("=" * 60)
    
    model = load_ieee39_model(json_path)
    
    if test_osm and not args.no_coords:
        print("\nAdding geographic coordinates to model components...")
        model = add_coordinates_to_model(model)
        with_coords = sum(1 for c in model.graph.nodes if c.coords is not None)
        print(f"  Components with coordinates: {with_coords} / {len(model.graph.nodes)}")
    
    if args.export:
        output_dir = os.path.join(project_root, "output")
        os.makedirs(output_dir, exist_ok=True)
        print(f"\nOutput directory: {output_dir}")
    
    if test_interactive:
        export_path = None
        if args.export:
            export_path = os.path.join(output_dir, "ieee39_interactive_graph.html")
        test_interactive_graph(model, show_names=args.names,
            show_types=args.types, export_path=export_path)
    
    if test_osm:
        export_path = None
        if args.export:
            export_path = os.path.join(output_dir, "ieee39_osm_map.html")
        test_osm_map(model, show_names=args.names, show_types=args.types,
            export_path=export_path, zoom_start=args.zoom)
    
    print("\n" + "=" * 60)
    print("Visualization Tests Complete")
    print("=" * 60)
    
    if args.export:
        print(f"\nOutput files saved to: {output_dir}")


if __name__ == "__main__":
    main()
