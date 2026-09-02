"""Test script for geographic plotting functionality."""

import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend for testing

from epowcore.gdf.bus import Bus, BusType, LFBusType
from epowcore.gdf.core_model import CoreModel
from epowcore.gdf.external_grid import ExternalGrid
from epowcore.gdf.load import Load
from epowcore.gdf.tline import TLine


def test_empty_model():
    """Test plotting with an empty model."""
    print("Testing empty model...")
    model = CoreModel(base_frequency=50.0)
    result = model.plot_geographic(show=False)
    assert result is None, "Empty model should return None"
    print("[PASS] Empty model test passed")


def test_model_without_coords():
    """Test plotting with components that have no coordinates."""
    print("\nTesting model without coordinates...")
    model = CoreModel(base_frequency=50.0)

    bus1 = Bus(uid=1, name="Bus1", lf_bus_type=LFBusType.PQ, nominal_voltage=110.0)
    bus2 = Bus(uid=2, name="Bus2", lf_bus_type=LFBusType.PV, nominal_voltage=110.0)

    model.add_component(bus1)
    model.add_component(bus2)
    model.graph.add_edge(bus1, bus2)

    result = model.plot_geographic(show=False)
    assert result is None, "Model without coordinates should return None"
    print("[PASS] Model without coordinates test passed")


def test_single_component_with_coords():
    """Test plotting with a single component that has coordinates."""
    print("\nTesting single component with coordinates...")
    model = CoreModel(base_frequency=50.0)

    bus1 = Bus(
        uid=1,
        name="Bus1",
        lf_bus_type=LFBusType.SL,
        nominal_voltage=110.0,
        coords=(51.5074, -0.1278),  # London
    )

    model.add_component(bus1)

    fig = model.plot_geographic(show=False)
    assert fig is not None, "Model with coordinates should return a figure"
    print("[PASS] Single component test passed")
    return fig


def test_multiple_components_with_connections():
    """Test plotting with multiple connected components."""
    print("\nTesting multiple components with connections...")
    model = CoreModel(base_frequency=50.0)

    # Create buses with coordinates
    bus1 = Bus(
        uid=1,
        name="London",
        lf_bus_type=LFBusType.SL,
        nominal_voltage=400.0,
        coords=(51.5074, -0.1278),  # London
    )
    bus2 = Bus(
        uid=2,
        name="Paris",
        lf_bus_type=LFBusType.PV,
        nominal_voltage=400.0,
        coords=(48.8566, 2.3522),  # Paris
    )
    bus3 = Bus(
        uid=3,
        name="Berlin",
        lf_bus_type=LFBusType.PQ,
        nominal_voltage=400.0,
        coords=(52.5200, 13.4050),  # Berlin
    )

    # Create load with coordinates
    load1 = Load(
        uid=4,
        name="Load_Paris",
        active_power=100.0,
        reactive_power=50.0,
        coords=(48.8566, 2.3522),  # Same as Paris
    )

    # Create transmission line with coordinates
    tline1 = TLine(
        uid=5,
        name="Line_London_Paris",
        r1=0.1,
        x1=0.5,
        b1=1e-6,
        rating=1000.0,
        coords=[(51.5074, -0.1278), (48.8566, 2.3522)],  # Multiple coords
    )

    # Add all components
    model.add_component(bus1)
    model.add_component(bus2)
    model.add_component(bus3)
    model.add_component(load1)
    model.add_component(tline1)

    # Add connections
    model.graph.add_edge(bus1, bus2)
    model.graph.add_edge(bus2, bus3)
    model.graph.add_edge(bus2, load1)

    # Test export
    export_path = "test_model_plot.png"
    fig = model.plot_geographic(show=False, export_path=export_path)
    assert fig is not None, "Model with coordinates should return a figure"

    # Verify file was created
    import os

    assert os.path.exists(export_path), f"Export file {export_path} should exist"
    print(f"[PASS] Export test passed - file saved to {export_path}")

    # Clean up
    os.remove(export_path)
    print("[PASS] Multiple components test passed")
    return fig


def test_mixed_components_some_without_coords():
    """Test plotting when some components have coordinates and others don't."""
    print("\nTesting mixed components (some with/without coords)...")
    model = CoreModel(base_frequency=50.0)

    bus1 = Bus(
        uid=1,
        name="Bus_With_Coords",
        lf_bus_type=LFBusType.SL,
        nominal_voltage=110.0,
        coords=(51.5074, -0.1278),
    )
    bus2 = Bus(uid=2, name="Bus_No_Coords", lf_bus_type=LFBusType.PQ, nominal_voltage=110.0)

    model.add_component(bus1)
    model.add_component(bus2)
    model.graph.add_edge(bus1, bus2)

    fig = model.plot_geographic(show=False)
    assert fig is not None, "Should plot components with coords even if some lack coords"
    print("[PASS] Mixed components test passed")


def test_figure_content():
    """Test that the generated figure has expected content."""
    print("\nTesting figure content...")
    model = CoreModel(base_frequency=50.0)

    bus1 = Bus(
        uid=1,
        name="TestBus",
        lf_bus_type=LFBusType.SL,
        nominal_voltage=110.0,
        coords=(51.5074, -0.1278),
    )
    model.add_component(bus1)

    fig = model.plot_geographic(show=False)
    assert fig is not None

    # Check figure has axes
    axes = fig.get_axes()
    assert len(axes) == 1, "Figure should have exactly one axis"
    ax = axes[0]

    # Check title
    assert ax.get_title() == "Geographic Model Visualization"

    # Check axis labels
    assert ax.get_xlabel() == "Longitude"
    assert ax.get_ylabel() == "Latitude"

    # Check there are scatter points plotted
    collections = ax.collections
    assert len(collections) > 0, "Should have at least one scatter collection"

    print("[PASS] Figure content test passed")


def test_list_coordinates():
    """Test plotting with components that have list of coordinates."""
    print("\nTesting components with list coordinates...")
    model = CoreModel(base_frequency=50.0)

    # TLine with multiple coordinate points along its path
    tline = TLine(
        uid=1,
        name="LongLine",
        r1=0.1,
        x1=0.5,
        b1=1e-6,
        rating=1000.0,
        coords=[(51.5074, -0.1278), (50.0, 1.0), (48.8566, 2.3522)],  # London  # Midpoint  # Paris
    )
    model.add_component(tline)

    fig = model.plot_geographic(show=False)
    assert fig is not None, "Should handle components with list coordinates"

    # The component should be plotted using the first coordinate
    axes = fig.get_axes()
    ax = axes[0]
    collections = ax.collections
    assert len(collections) > 0, "Should have scatter collection for line component"

    print("[PASS] List coordinates test passed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Running Geographic Plot Tests")
    print("=" * 60)

    test_empty_model()
    test_model_without_coords()
    test_single_component_with_coords()
    test_multiple_components_with_connections()
    test_mixed_components_some_without_coords()
    test_figure_content()
    test_list_coordinates()

    print("\n" + "=" * 60)
    print("All tests passed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
