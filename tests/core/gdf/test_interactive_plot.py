"""Test script for interactive graph and OSM map plotting functionality."""

import os
import tempfile

from epowcore.gdf.bus import Bus, LFBusType
from epowcore.gdf.core_model import CoreModel
from epowcore.gdf.load import Load
from epowcore.gdf.generators import StaticGenerator


def test_empty_model_plot_interactive():
    """Test plot_interactive_graph with an empty model."""
    print("Testing interactive graph with empty model...")
    model = CoreModel(base_frequency=50.0)
    result = model.plot_interactive_graph()
    assert result is None, "Empty model should return None"
    print("[PASS] Empty model test passed")


def test_empty_model_plot_osm():
    """Test plot_osm_map with an empty model."""
    print("\nTesting OSM map with empty model...")
    model = CoreModel(base_frequency=50.0)
    result = model.plot_osm_map()
    assert result is None, "Empty model should return None"
    print("[PASS] Empty model test passed")


def test_model_without_coords_plot_interactive():
    """Test plot_interactive_graph with components that have no coordinates."""
    print("\nTesting interactive graph without coordinates...")
    model = CoreModel(base_frequency=50.0)
    bus1 = Bus(uid=1, name="Bus1", lf_bus_type=LFBusType.PQ, nominal_voltage=110.0)
    bus2 = Bus(uid=2, name="Bus2", lf_bus_type=LFBusType.PV, nominal_voltage=110.0)
    model.add_component(bus1)
    model.add_component(bus2)
    model.graph.add_edge(bus1, bus2)

    result = model.plot_interactive_graph()
    assert result is not None, "Should return HTML even without coordinates"
    assert "<div" in result, "Should contain HTML div elements"
    print("[PASS] No coordinates test passed")


def test_model_without_coords_plot_osm():
    """Test plot_osm_map with components that have no coordinates."""
    print("\nTesting OSM map without coordinates...")
    model = CoreModel(base_frequency=50.0)
    bus1 = Bus(uid=1, name="Bus1", lf_bus_type=LFBusType.PQ, nominal_voltage=110.0)
    bus2 = Bus(uid=2, name="Bus2", lf_bus_type=LFBusType.PV, nominal_voltage=110.0)
    model.add_component(bus1)
    model.add_component(bus2)
    model.graph.add_edge(bus1, bus2)

    result = model.plot_osm_map()
    assert result is None, "Should return None when no components have coordinates"
    print("[PASS] No coordinates test passed")


def test_single_component_with_coords():
    """Test both plots with a single component that has coordinates."""
    print("\nTesting single component with coordinates (interactive)...")
    model = CoreModel(base_frequency=50.0)
    bus1 = Bus(
        uid=1, name="London", lf_bus_type=LFBusType.SL,
        nominal_voltage=110.0, coords=(51.5074, -0.1278)
    )
    model.add_component(bus1)

    html = model.plot_interactive_graph()
    assert html is not None, "Should return HTML string"
    assert "<div" in html, "Should contain HTML div elements"
    assert "Interactive Network Graph" in html, "Should contain title"
    print("[PASS] Single component (interactive) test passed")

    print("\nTesting single component with coordinates (OSM)...")
    result = model.plot_osm_map()
    assert result is not None, "Should return HTML with valid coordinates"
    assert "<div" in result or "<html" in result.lower(), "Should contain HTML"
    print("[PASS] Single component (OSM) test passed")


def test_multiple_components_with_connections():
    """Test plotting with multiple connected components."""
    print("\nTesting multiple connected components (interactive)...")
    model = CoreModel(base_frequency=50.0)

    bus1 = Bus(
        uid=1, name="London", lf_bus_type=LFBusType.SL,
        nominal_voltage=400.0, coords=(51.5074, -0.1278)
    )
    bus2 = Bus(
        uid=2, name="Paris", lf_bus_type=LFBusType.PV,
        nominal_voltage=400.0, coords=(48.8566, 2.3522)
    )
    bus3 = Bus(
        uid=3, name="Berlin", lf_bus_type=LFBusType.PQ,
        nominal_voltage=400.0, coords=(52.5200, 13.4050)
    )
    load1 = Load(
        uid=4, name="Load_Paris",
        active_power=100.0, reactive_power=50.0,
        coords=(48.8566, 2.3522)
    )
    gen1 = StaticGenerator(
        uid=5, name="Gen_London",
        active_power=500.0, reactive_power=100.0,
        rated_apparent_power=600.0, rated_active_power=500.0,
        voltage_set_point=1.0, p_min=0.0, p_max=1000.0,
        q_min=-500.0, q_max=500.0,
        coords=(51.5074, -0.1278)
    )

    model.add_component(bus1)
    model.add_component(bus2)
    model.add_component(bus3)
    model.add_component(load1)
    model.add_component(gen1)
    model.graph.add_edge(bus1, bus2)
    model.graph.add_edge(bus2, bus3)
    model.graph.add_edge(bus2, load1)
    model.graph.add_edge(bus1, gen1)

    html = model.plot_interactive_graph()
    assert html is not None
    assert "Interactive Network Graph" in html
    print("[PASS] Multiple components (interactive) test passed")

    print("\nTesting multiple connected components (OSM)...")
    osm_html = model.plot_osm_map()
    assert osm_html is not None
    print("[PASS] Multiple components (OSM) test passed")


def test_plot_interactive_with_names():
    """Test interactive graph with show_names enabled."""
    print("\nTesting interactive graph with show_names=True...")
    model = CoreModel(base_frequency=50.0)
    bus1 = Bus(
        uid=1, name="Bus_With_Name", lf_bus_type=LFBusType.SL,
        nominal_voltage=110.0, coords=(51.5074, -0.1278)
    )
    model.add_component(bus1)

    html = model.plot_interactive_graph(show_names=True)
    assert html is not None
    assert "Bus_With_Name" in html
    print("[PASS] show_names test passed")


def test_plot_osm_with_names():
    """Test OSM map with show_names enabled."""
    print("\nTesting OSM map with show_names=True...")
    model = CoreModel(base_frequency=50.0)
    bus1 = Bus(
        uid=1, name="TestBus", lf_bus_type=LFBusType.SL,
        nominal_voltage=110.0, coords=(51.5074, -0.1278)
    )
    model.add_component(bus1)

    html = model.plot_osm_map(show_names=True)
    assert html is not None
    assert "TestBus" in html
    print("[PASS] show_names test passed")


def test_plot_interactive_with_types():
    """Test interactive graph with show_types enabled."""
    print("\nTesting interactive graph with show_types=True...")
    model = CoreModel(base_frequency=50.0)
    bus1 = Bus(
        uid=1, name="Bus1", lf_bus_type=LFBusType.SL,
        nominal_voltage=110.0, coords=(51.5074, -0.1278)
    )
    load1 = Load(
        uid=2, name="Load1",
        active_power=100.0, reactive_power=50.0,
        coords=(48.8566, 2.3522)
    )
    model.add_component(bus1)
    model.add_component(load1)
    model.graph.add_edge(bus1, load1)

    html = model.plot_interactive_graph(show_types=True)
    assert html is not None
    assert "Bus" in html or "Load" in html
    print("[PASS] show_types test passed")


def test_plot_osm_with_types():
    """Test OSM map with show_types enabled."""
    print("\nTesting OSM map with show_types=True...")
    model = CoreModel(base_frequency=50.0)
    bus1 = Bus(
        uid=1, name="Bus1", lf_bus_type=LFBusType.SL,
        nominal_voltage=110.0, coords=(51.5074, -0.1278)
    )
    model.add_component(bus1)

    html = model.plot_osm_map(show_types=True)
    assert html is not None
    print("[PASS] show_types test passed")
def test_plot_interactive_export_html():
    """Test interactive graph export to HTML file."""
    print("\nTesting interactive graph export to HTML...")
    model = CoreModel(base_frequency=50.0)
    bus1 = Bus(
        uid=1, name="Bus1", lf_bus_type=LFBusType.SL,
        nominal_voltage=110.0, coords=(51.5074, -0.1278)
    )
    model.add_component(bus1)

    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = os.path.join(tmpdir, "test_network.html")
        result = model.plot_interactive_graph(export_path=export_path)
        assert result is None, "Should return None when exporting to file"
        assert os.path.exists(export_path), f"HTML file should exist at {export_path}"
        with open(export_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Interactive Network Graph" in content
        print("[PASS] Export to HTML test passed")


def test_plot_osm_export_html():
    """Test OSM map export to HTML file."""
    print("\nTesting OSM map export to HTML...")
    model = CoreModel(base_frequency=50.0)
    bus1 = Bus(
        uid=1, name="Bus1", lf_bus_type=LFBusType.SL,
        nominal_voltage=110.0, coords=(51.5074, -0.1278)
    )
    model.add_component(bus1)

    with tempfile.TemporaryDirectory() as tmpdir:
        export_path = os.path.join(tmpdir, "test_map.html")
        result = model.plot_osm_map(export_path=export_path)
        html_path = export_path
        if not html_path.endswith(".html"):
            html_path = export_path + ".html"
        assert os.path.exists(html_path), f"HTML file should exist at {html_path}"
        print("[PASS] Export to HTML test passed")


def test_plot_osm_zoom_level():
    """Test OSM map with custom zoom level."""
    print("\nTesting OSM map with custom zoom level...")
    model = CoreModel(base_frequency=50.0)
    bus1 = Bus(
        uid=1, name="Bus1", lf_bus_type=LFBusType.SL,
        nominal_voltage=110.0, coords=(51.5074, -0.1278)
    )
    model.add_component(bus1)

    html = model.plot_osm_map(zoom_start=15)
    assert html is not None
    print("[PASS] Custom zoom level test passed")


def test_plot_with_tline_coords():
    """Test plots with TLine components that have multiple coordinates."""
    print("\nTesting with TLine components that have multiple coordinates...")
    from epowcore.gdf.tline import TLine
    model = CoreModel(base_frequency=50.0)

    bus1 = Bus(
        uid=1, name="London", lf_bus_type=LFBusType.SL,
        nominal_voltage=400.0, coords=(51.5074, -0.1278)
    )
    bus2 = Bus(
        uid=2, name="Paris", lf_bus_type=LFBusType.PQ,
        nominal_voltage=400.0, coords=(48.8566, 2.3522)
    )
    tline = TLine(
        uid=3, name="Line_London_Paris",
        r1=0.1, x1=0.5, b1=1e-6, rating=1000.0,
        coords=[(51.5074, -0.1278), (48.8566, 2.3522)]
    )

    model.add_component(bus1)
    model.add_component(bus2)
    model.add_component(tline)
    model.graph.add_edge(bus1, bus2)

    html_interactive = model.plot_interactive_graph()
    assert html_interactive is not None
    print("[PASS] Interactive with TLine coords test passed")

    html_osm = model.plot_osm_map()
    assert html_osm is not None
    print("[PASS] OSM with TLine coords test passed")


def test_mixed_components_with_without_coords():
    """Test when some components have coordinates and others don't."""
    print("\nTesting mixed components (some with/without coords)...")
    model = CoreModel(base_frequency=50.0)

    bus1 = Bus(
        uid=1, name="Bus_With_Coords", lf_bus_type=LFBusType.SL,
        nominal_voltage=110.0, coords=(51.5074, -0.1278)
    )
    bus2 = Bus(
        uid=2, name="Bus_No_Coords", lf_bus_type=LFBusType.PQ,
        nominal_voltage=110.0
    )
    model.add_component(bus1)
    model.add_component(bus2)
    model.graph.add_edge(bus1, bus2)

    html_interactive = model.plot_interactive_graph()
    assert html_interactive is not None
    print("[PASS] Mixed components (interactive) test passed")

    html_osm = model.plot_osm_map()
    assert html_osm is not None
    print("[PASS] Mixed components (OSM) test passed")


def main():
    """Run all tests."""
    print("=" * 70)
    print("Running Interactive & OSM Plot Tests")
    print("=" * 70)

    test_empty_model_plot_interactive()
    test_empty_model_plot_osm()
    test_model_without_coords_plot_interactive()
    test_model_without_coords_plot_osm()
    test_single_component_with_coords()
    test_multiple_components_with_connections()
    test_plot_interactive_with_names()
    test_plot_osm_with_names()
    test_plot_interactive_with_types()
    test_plot_osm_with_types()
    test_plot_interactive_export_html()
    test_plot_osm_export_html()
    test_plot_osm_zoom_level()
    test_plot_with_tline_coords()
    test_mixed_components_with_without_coords()

    print("\n" + "=" * 70)
    print("All tests passed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()