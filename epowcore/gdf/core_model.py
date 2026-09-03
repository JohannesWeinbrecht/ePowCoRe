import importlib
from ast import literal_eval as make_tuple
from dataclasses import asdict, dataclass, field
from typing import TypeVar

import matplotlib
import networkx as nx
import numpy as np
from matplotlib.figure import Figure

from epowcore.generic.component_graph import ComponentGraph
from epowcore.generic.configuration import Configuration
from epowcore.generic.constants import GDF_VERSION, Platform
from epowcore.generic.logger import Logger

from .component import Component

T = TypeVar("T")


@dataclass(kw_only=True)
class CoreModel:
    """This class represents the generic model, including the component graph and additional attributes."""

    base_frequency: float
    """Base Frequency of the elements based of the project."""
    base_mva: float | None = None
    """Base rating for pu calculations in the project."""
    graph: ComponentGraph = field(default_factory=ComponentGraph)
    """Graph of connection between elements."""
    version: int = GDF_VERSION
    """Version of the generic data format."""

    def base_mva_fb(self, platform: Platform | None = None) -> float:
        """Base rating for pu calculations in the project with fallback."""
        if self.base_mva is not None:
            return self.base_mva
        default = Configuration().get_default("CoreModel", "base_mva", platform)
        if default is None:
            raise ValueError("Could not find default value for CoreModel.base_mva")
        Logger.log_to_selected(
            f"Using default for {type(self).__name__}: base_mva = {default}"
        )
        return default

    def add_component(self, component: Component) -> None:
        """Add a component to the graph.

        :param component: The component to be added.
        :type component: Component
        """
        self.graph.add_node(component)

    def remove_component(
        self, component: Component, keep_connections: bool = False
    ) -> None:
        """Remove a component from the graph.

        :param component: The component to be removed.
        :type component: Component
        """
        if keep_connections:
            edges: list[tuple[Component, list[str]]] = []
            for l, r, edge_data in self.graph.edges.data(component):
                neighbor = l if l.uid != component.uid else r
                if neighbor.uid in edge_data:
                    edges.append(
                        (
                            neighbor,
                            edge_data[neighbor.uid],
                        )
                    )
            for i, edge1 in enumerate(edges):
                for edge2 in edges[i + 1 :]:
                    self.add_connection(
                        edge1[0],
                        edge2[0],
                        edge1[1],
                        edge2[1],
                    )
        self.graph.remove_node(component)

    def get_component_by_id(
        self, uid: int
    ) -> tuple[Component | None, ComponentGraph | None]:
        """Get a component by its uid.

        :param uid: The uid of the component.
        :type uid: int
        :return: The component.
        :rtype: Component
        """
        from epowcore.gdf.subsystem import Subsystem

        for component in self.graph.nodes:
            if component.uid == uid:
                return component, self.graph
            if isinstance(component, Subsystem):
                result, graph = component.get_component_by_id(uid)
                if result is not None:
                    return result, graph
        return None, None

    def add_connection(
        self,
        component1: Component,
        component2: Component,
        connector_name1: str | list[str] | None = "",
        connector_name2: str | list[str] | None = "",
    ) -> None:
        """Add an edge between two components to the graph.

        :param component1: The first component.
        :type component1: Component
        :param component2: The second component.
        :type component2: Component
        :param connector_name1: The name of the connector on the first component.
        :type connector_name1: str | list[str] | None
        :param connector_name2: The name of the connector on the second component.
        :type connector_name2: str | list[str] | None
        """
        # we don't want to manipulate the given lists when concatenating
        if isinstance(connector_name1, list):
            connector_name1 = connector_name1.copy()
        if isinstance(connector_name2, list):
            connector_name2 = connector_name2.copy()
        if connector_name1 is None:
            connector_name1 = []
        if connector_name2 is None:
            connector_name2 = []
        if isinstance(connector_name1, str):
            connector_name1 = [connector_name1]
        if isinstance(connector_name2, str):
            connector_name2 = [connector_name2]
        attrs = {}
        if self.graph.has_edge(component1, component2):
            attrs = self.graph.edges[component1, component2]
            if component1.uid in attrs:
                attrs[component1.uid] += connector_name1
            else:
                attrs[component1.uid] = connector_name1
            if component2.uid in attrs:
                attrs[component2.uid] += connector_name2
            else:
                attrs[component2.uid] = connector_name2
        else:
            attrs = {
                component1.uid: connector_name1,
                component2.uid: connector_name2,
            }
            self.graph.add_edge(component1, component2)
        self.graph.edges.update(component1, component2, attrs)

    # TODO This is kept for legacy reasons. Has only been used without following subsystems and ports.
    def get_attached_to(
        self,
        component: Component,
        connector_name: str | None = None,
    ) -> list[tuple[Component, list[str]]]:
        """Get the components attached to a component. Optionally filtered by connector name.

        :param component: The source component.
        :type component: Component
        :param connector_name: The name of the connector. If None, all neighbors are returned.
        :type connector_name: str
        :param include_subsystems: If True, connections to Subsystems and Ports are resolved to the component connected to this port/subsystem.
        :type include_subsystems: bool
        :return: A list of components attached to the connector and their port name.
        :rtype: list[Component, list[str]]
        """
        result: list[tuple[Component, list[str]]] = []
        if connector_name is None:
            # If no connector name is given, return all neighbors
            for c in self.graph.neighbors(component):
                # Check for connector name
                if c.uid in self.graph.edges[component, c]:
                    result.append((c, self.graph.edges[component, c][c.uid]))
                else:
                    result.append((c, [""]))
        else:
            edges = self.graph.edges.data()
            for edge in edges:
                if (
                    component.uid in edge[2]
                    and connector_name in edge[2][component.uid]
                ):
                    for k, value in edge[2].items():
                        if k != component.uid:
                            if edge[0].uid == component.uid:
                                result.append((edge[1], value))
                            else:
                                result.append((edge[0], value))
        return result

    def get_corresponding_connector(
        self, component: Component, neighbor: Component, connector_name: str
    ) -> str | None:
        """Get the corresponding connector name of a component to a neighbor component.

        :param component: The component.
        :param neighbor: The neighbor component.
        :param connector_name: The name of the connector.
        :return: The corresponding connector name. None if no corresponding connector exists.
        """
        if not self.graph.has_edge(component, neighbor):
            return None
        if component.uid not in self.graph.edges[component, neighbor]:
            return None
        if connector_name not in self.graph.edges[component, neighbor][component.uid]:
            return None
        index = self.graph.edges[component, neighbor][component.uid].index(
            connector_name
        )
        if len(self.graph.edges[component, neighbor][neighbor.uid]) != len(
            self.graph.edges[component, neighbor][component.uid]
        ):
            raise ValueError("The number of connectors does not match.")
        return self.graph.edges[component, neighbor][neighbor.uid][index]

    def get_connector_names(self, component: Component) -> list[str]:
        """Get the names of all connectors of a component.

        :param component: The component.
        :type component: Component
        :return: A list of connector names.
        :rtype: list[str]
        """
        edges = self.graph.edges.attr(component.uid)
        return [a for b in [x[2] for x in edges if x[2] is not None] for a in b]

    def get_connection_name(
        self, component: Component, neighbor: Component
    ) -> list[str] | None:
        """Get the connector name of the neighbor.

        :param component: The component with the connector.
        :type component: Component
        :param neighbor: The component connected to the connector.
        :type neighbor: Component
        :return: The name of the connector.
        :rtype: list[str] | None
        """
        if not self.graph.has_edge(component, neighbor):
            return None
        if neighbor.uid not in self.graph.edges[component, neighbor]:
            return None
        return self.graph.edges[component, neighbor][neighbor.uid]

    def check_connectors(self, component: Component) -> bool:
        """Checks if the component only has connectors according to its type.

        :param component: The component.
        :type component: Component
        :return: True if the component only has valid connectors, else False.
        :rtype: bool
        """
        for connector in self.get_connector_names(component):
            if not connector in component.connector_names:
                return False
        return True

    def has_connected_to(self, component: Component, connector_name: str) -> bool:
        """Checks if the component has a connection to a specific connector.

        :param component: The component.
        :type component: Component
        :param connector_name: The name of the connector.
        :type connector_name: str
        :return: True if the component has a connection to the connector, else False.
        :rtype: bool
        """
        return len(self.get_attached_to(component, connector_name)) > 0

    def get_neighbors(
        self,
        component: Component,
        follow_links: bool = True,
        connector: str | None = None,
    ) -> list[Component]:
        """Get the direct neighbors of [component].
        Can optionally traverse subsystems and restrict looking for neighbors at a specified [connector].

        :param component: The component whose neighbors are returned.
        :type component: Component
        :param follow_links: If true, replace Subsystems and Ports with the component they actually connect to; defaults to True
        :type follow_links: bool, optional
        :param connector: If not None, limit only return neighbors connected to this connector; defaults to None
        :type connector: str | None, optional
        :return: A list of components connected to to given [component].
        :rtype: list[Component]
        """
        from epowcore.gdf.port import Port
        from epowcore.gdf.subsystem import Subsystem

        _, graph = self.get_component_by_id(component.uid)
        if graph is None:
            return []

        neighbors: list[Component]

        if connector is not None:
            neighbors = []
            edge_data = graph.edges.data(component)
            for _, neighbor, data in edge_data:
                connectors = data[component.uid]
                if connector in connectors:
                    neighbors.append(neighbor)
        else:
            neighbors = list(graph.neighbors(component))

        if follow_links:
            # replace ports and subsystems as long as there are any in the list
            while any(isinstance(n, (Port, Subsystem)) for n in neighbors):
                new_neighbors = []
                for n in neighbors:
                    if isinstance(n, Port):
                        # get the component that the port represents in the subsystem
                        connected_component = self.get_component_by_id(
                            n.connection_component
                        )[0]
                        if connected_component is not None:
                            new_neighbors.append(connected_component)
                    elif isinstance(n, Subsystem):
                        # get the components that are connected to the corresponding port inside the subsystem
                        new_neighbors.extend(n.get_connected_to_port(component.uid))
                    else:
                        new_neighbors.append(n)
                neighbors = new_neighbors
        return neighbors

    def type_list(self, comp_type: type[T] | list[type[T]]) -> list[T]:
        """List of components of type [comp_type]."""
        if isinstance(comp_type, list):
            return [x for x in self.graph.nodes if isinstance(x, tuple(comp_type))]  # type: ignore
        return [x for x in self.graph.nodes if isinstance(x, comp_type)]

    def component_list(self) -> list[Component]:
        """List of all components."""
        return list(self.graph.nodes)

    def get_valid_id(self) -> int:
        """Generate a valid new component ID by calculating the maximum taken ID.

        :return: A valid ID for a new component.
        :rtype: int
        """
        if len(self.graph.nodes) == 0:
            return 0
        max_id = max(n.uid for n in self.graph.nodes)
        from epowcore.gdf.subsystem import Subsystem

        for s in self.type_list(Subsystem):
            s_max = s.get_max_id()
            if s_max > max_id:
                max_id = s_max
        return max_id + 1

    def sanity_check(self) -> bool:
        """Checks the validity of the model.

        :return: True if the model is valid, else False.
        """

        graph_sanity = self.graph.sanity_check()
        # Check if the edges have the required connectors
        connector_check = all(
            map(
                lambda node: (
                    len(node.connector_names) == 0
                    or all(
                        map(
                            lambda x: self.has_connected_to(node, x),
                            node.connector_names,
                        )
                    )
                ),
                self.graph.nodes,
            )
        )

        # Check if the nodes have unique IDs
        unique_ids_check = len(self.graph.nodes) == len(
            set((node.uid for node in self.graph.nodes))
        )
        return graph_sanity and connector_check and unique_ids_check

    def export_dict(self) -> dict:
        """Export the whole model as a dictionary.
        The dictionary only contains primitive values and thus can be encoded as JSON.

        :return: The dictionary containing the model settings, graph, and components.
        :rtype: dict
        """
        data = asdict(self)
        del data["graph"]
        return data | self.graph.to_primitive_dict()

    @classmethod
    def import_dict(cls, data: dict) -> "CoreModel":
        """Import a valid dictionary and return a CoreModel representation of the model.

        :param data: The dictionary containing the model data.
        :type data: dict
        :return: The CoreModel representation of the model.
        :rtype: CoreModel
        """
        version = data.get("version", None)
        if version is None or version != GDF_VERSION:
            raise ValueError(
                f"Version of data doesn't match version of CoreModel: {version} != {GDF_VERSION}"
            )
        import_data = dict(data)
        import_comp_dict = data["components"]
        label_dict = {}
        class_dict = {}
        for key_str, comp_data in import_comp_dict.items():
            key = make_tuple(key_str)
            if key[0] not in class_dict:
                klass = _get_class(key[0])
                class_dict[key[0]] = klass
            else:
                klass = class_dict[key[0]]
            component = klass.from_primitive_dict(comp_data)
            label_dict[key_str] = component
        import_graph = nx.from_dict_of_dicts(import_data["graph"])
        # convert edge keys from string to int
        for _, _, d in import_graph.edges.data():
            for key, value in list(d.items()):
                if key in d and not isinstance(key, int):
                    d[int(key)] = value
                    del d[key]
        import_data["graph"] = ComponentGraph(
            nx.relabel_nodes(import_graph, label_dict)
        )
        del import_data["components"]
        return cls(**import_data)

    def plot_geographic(
        self, show: bool = True, export_path: str | None = None
    ) -> Figure | None:
        """Create a geographic plot of the core model showing component locations and connections.

        :param show: Whether to display the plot interactively, defaults to True
        :type show: bool, optional
        :param export_path: Path to save the image file (e.g., "model.png"), defaults to None
        :type export_path: str | None, optional
        :return: The matplotlib Figure object if successful, None if no components have coordinates
        :rtype: matplotlib.figure.Figure | None
        """
        print("Starting plotting")
        import matplotlib.pyplot as plt
        from matplotlib.collections import LineCollection

        # Get all components from the graph
        components = list(self.graph.nodes)

        if not components:
            Logger.log_to_selected("Warning: No components in model to plot.")
            return None

        # Collect components with valid coordinates
        components_with_coords: list[Component] = []
        coords_list: list[tuple[float, float]] = []

        for comp in components:
            coords = comp.coords
            if coords is None:
                continue

            # Handle both single coordinate pair and list of coordinate pairs
            if isinstance(coords, tuple) and len(coords) == 2:
                components_with_coords.append(comp)
                coords_list.append(coords)
            elif isinstance(coords, list) and len(coords) > 0:
                components_with_coords.append(comp)
                coords_list.append(coords[0])

        print("are we logging here?")
        if not components_with_coords:
            print("No cords herer")
            Logger.log_to_selected(
                "Warning: No components with valid coordinates found in model."
            )
            return None

        # Extract longitude (x) and latitude (y) - coords are (lat, lon)
        lats = [coord[0] for coord in coords_list]
        lons = [coord[1] for coord in coords_list]

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(10, 8))

        # Define color map for different component types
        component_types = sorted(
            set(type(comp).__name__ for comp in components_with_coords)
        )
        type_colors = plt.cm.tab10(np.linspace(0, 1, len(component_types)))
        type_color_map = {
            type_name: type_colors[i] for i, type_name in enumerate(component_types)
        }

        # Define markers for different component types
        marker_cycle = ["o", "s", "^", "D", "v", "<", ">", "p", "h", "*"]
        type_marker_map = {
            type_name: marker_cycle[i % len(marker_cycle)]
            for i, type_name in enumerate(component_types)
        }

        # Plot each component with its type-specific color and marker
        for comp, lat, lon in zip(components_with_coords, lats, lons):
            type_name = type(comp).__name__
            color = type_color_map[type_name]
            marker = type_marker_map[type_name]

            ax.scatter(
                lon,
                lat,
                c=[color],
                marker=marker,
                s=100,
                label=type_name,
                edgecolors="black",
                linewidths=0.5,
                zorder=3,
            )

            # Add component name as annotation
            ax.annotate(
                comp.name,
                (lon, lat),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8,
                alpha=0.7,
            )

        # Draw connections (edges) between components
        line_segments = []
        for u, v in self.graph.edges:
            u_coords = None
            v_coords = None

            if u.coords is not None:
                if isinstance(u.coords, tuple) and len(u.coords) == 2:
                    u_coords = (u.coords[1], u.coords[0])
                elif isinstance(u.coords, list) and len(u.coords) > 0:
                    u_coords = (u.coords[0][1], u.coords[0][0])

            if v.coords is not None:
                if isinstance(v.coords, tuple) and len(v.coords) == 2:
                    v_coords = (v.coords[1], v.coords[0])
                elif isinstance(v.coords, list) and len(v.coords) > 0:
                    v_coords = (v.coords[0][1], v.coords[0][0])

            if u_coords is not None and v_coords is not None:
                line_segments.append([u_coords, v_coords])

        if line_segments:
            lc = LineCollection(
                line_segments, colors="gray", linewidths=1, alpha=0.5, zorder=1
            )
            ax.add_collection(lc)

        # Remove duplicate labels for legend
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            ax.legend(
                by_label.values(),
                by_label.keys(),
                loc="best",
                framealpha=0.9,
                fontsize=9,
            )

        # Set labels and title
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_title("Geographic Model Visualization")
        ax.grid(True, alpha=0.3)
        ax.set_aspect("equal", adjustable="datalim")
        plt.tight_layout()

        # Export if path provided
        if export_path is not None:
            fig.savefig(export_path, dpi=150, bbox_inches="tight")
            Logger.log_to_selected(f"Geographic plot saved to: {export_path}")

            # Show if requested
        print("lkajsdölfakjsdöfljk")
        plt.show()
        if show:
            pass
        else:
            return fig

        return None

    def plot_interactive_graph(
        self,
        show_names: bool = False,
        show_types: bool = False,
        export_path: str | None = None,
    ) -> str | None:
        """Create an interactive network graph visualization using Plotly.

        This method generates an interactive HTML visualization of the network topology,
        where nodes represent components and edges represent connections between them.
        The visualization supports zooming, panning, and hovering for detailed information.

        :param show_names: Whether to display component names as labels on nodes,
            defaults to False (recommended for large models to avoid performance issues)
        :type show_names: bool, optional
        :param show_types: Whether to color nodes by component type (e.g., Bus, Load, Line),
            defaults to False (recommended for large models to avoid performance issues)
        :type show_types: bool, optional
        :param export_path: Path to save the interactive HTML file, e.g., "network.html".
            If None, the HTML string is returned directly, defaults to None
        :type export_path: str | None, optional
        :return: HTML string containing the interactive visualization if export_path is None,
            otherwise None on successful save
        :rtype: str | None
        """
        import plotly.graph_objects as go

        components = list(self.graph.nodes)

        if not components:
            Logger.log_to_selected("Warning: No components in model to plot.")
            return None

        # Extract positions for nodes - use geographic coordinates if available
        pos_data: dict[Component, tuple[float, float]] = {}
        coords_components: list[Component] = []
        coords_list: list[tuple[float, float]] = []

        for comp in components:
            coords = comp.coords
            if coords is None:
                continue
            if isinstance(coords, tuple) and len(coords) == 2:
                coords_components.append(comp)
                coords_list.append((coords[1], coords[0]))  # lon, lat
            elif isinstance(coords, list) and len(coords) > 0:
                coords_components.append(comp)
                coords_list.append((coords[0][1], coords[0][0]))

        # Build position map from geographic coordinates
        for comp, (x, y) in zip(coords_components, coords_list):
            pos_data[comp] = (x, y)

        # Place components without coords near their first connected neighbor
        for comp in components:
            if comp not in pos_data:
                for neighbor in self.graph.neighbors(comp):
                    if neighbor in pos_data:
                        nx_pos, ny_pos = pos_data[neighbor]
                        pos_data[comp] = (nx_pos + 0.001, ny_pos + 0.001)
                        break

        # Grid fallback for truly isolated components
        if coords_components:
            center_lon = sum(p[0] for p in pos_data.values()) / len(pos_data)
            center_lat = sum(p[1] for p in pos_data.values()) / len(pos_data)
        else:
            center_lon, center_lat = 0.0, 0.0

        for comp in components:
            if comp not in pos_data:
                idx = list(components).index(comp)
                pos_data[comp] = (
                    center_lon + (idx % 10) * 0.01,
                    center_lat + (idx // 10) * 0.01,
                )

        # Build edge traces
        edge_x: list[float] = []
        edge_y: list[float] = []
        for u, v in self.graph.edges:
            if u in pos_data and v in pos_data:
                x0, y0 = pos_data[u]
                x1, y1 = pos_data[v]
                edge_x.extend([x0, x1, None])
                edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            line=dict(width=1.5, color="#888"),
            hoverinfo="none",
            mode="lines",
            showlegend=False,
        )

        # Build node traces
        node_x: list[float] = []
        node_y: list[float] = []
        node_text: list[str] = []
        node_color: list[str] = []

        component_types = sorted(set(type(c).__name__ for c in components))
        type_to_color = {}
        color_palette = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
        ]
        for i, t in enumerate(component_types):
            type_to_color[t] = color_palette[i % len(color_palette)]

        for comp in components:
            if comp not in pos_data:
                continue
            x, y = pos_data[comp]
            node_x.append(x)
            node_y.append(y)
            comp_type = type(comp).__name__
            node_text.append(
                f"{comp.name} ({comp_type})" if show_names else comp_type
            )
            node_color.append(type_to_color.get(comp_type, "#17becf"))

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode="markers",
            hoverinfo="text",
            text=node_text,
            marker=dict(
                showscale=show_types,
                colorscale="Viridis",
                reversescale=True,
                color=node_color,
                size=12,
                colorbar=dict(
                    thickness=15,
                    title="Component Type",
                    xanchor="left",
                    title_side="right",
                ) if show_types else None,
                line_width=1,
            ),
            showlegend=False,
        )

        # Assemble figure
        layout = go.Layout(
            title=dict(text="Interactive Network Graph", font=dict(size=20)),
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=60),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=800,
            width=1200,
            template="plotly_white",
        )

        if show_names:
            annotations = [
                dict(
                    x=x, y=y,
                    text=comp.name,
                    showarrow=False,
                    xanchor="left",
                    yanchor="bottom",
                    font=dict(size=10, color="black"),
                    bgcolor="rgba(255,255,255,0.7)",
                    borderpad=2,
                )
                for comp, (x, y) in pos_data.items()
            ]
            layout.annotations = annotations

        fig = go.Figure(data=[edge_trace, node_trace], layout=layout)

        if show_types and component_types:
            for comp_type in component_types:
                fig.add_trace(
                    go.Scatter(
                        x=[None], y=[None],
                        mode="markers",
                        marker=dict(size=12, color=type_to_color[comp_type]),
                        name=comp_type,
                        showlegend=True,
                    )
                )
            fig.update_layout(
                showlegend=True,
                legend_title_text="Component Types",
                legend=dict(x=1.0, y=1.0),
            )

        if export_path is not None:
            fig.write_html(export_path)
            Logger.log_to_selected(f"Interactive graph saved to: {export_path}")
            return None
        else:
            return fig.to_html(full_html=True, include_plotlyjs="cdn")

    def plot_osm_map(
        self,
        show_names: bool = False,
        show_types: bool = False,
        export_path: str | None = None,
        zoom_start: int = 10,
    ) -> str | None:
        """Create a geographic network plot overlaid on an OpenStreetMap background using Folium.

        This method generates an interactive map showing component locations and their
        connections, displayed on OpenStreetMap tiles. Optionally exports to a static image.

        :param show_names: Whether to display component names as popup/tooltips on markers,
            defaults to False (recommended for large models to avoid performance issues)
        :type show_names: bool, optional
        :param show_types: Whether to display a legend and color markers by component type,
            defaults to False (recommended for large models to avoid performance issues)
        :type show_types: bool, optional
        :param export_path: Path to save the image file (e.g., "map.png", "map.jpg").
            Supports PNG, JPEG, and WebP formats. Requires selenium and chrome driver to be
            installed for image export, defaults to None
        :type export_path: str | None, optional
        :param zoom_start: Initial zoom level for the map (1-18, higher = more zoomed in),
            defaults to 10
        :type zoom_start: int, optional
        :return: Folium Map HTML file path if export_path is None and map is saved,
            or None if export_path is provided or on failure
        :rtype: str | None
        """
        import folium
        from folium import plugins

        components = list(self.graph.nodes)

        if not components:
            Logger.log_to_selected("Warning: No components in model to plot.")
            return None

        # Collect components with valid coordinates
        components_with_coords: list[Component] = []
        coords_list: list[tuple[float, float]] = []

        for comp in components:
            coords = comp.coords
            if coords is None:
                continue
            if isinstance(coords, tuple) and len(coords) == 2:
                components_with_coords.append(comp)
                coords_list.append((coords[0], coords[1]))  # lat, lon
            elif isinstance(coords, list) and len(coords) > 0:
                components_with_coords.append(comp)
                coords_list.append((coords[0][0], coords[0][1]))

        if not components_with_coords:
            Logger.log_to_selected(
                "Warning: No components with valid coordinates found in model."
            )
            return None

        # Calculate map center
        avg_lat = sum(c[0] for c in coords_list) / len(coords_list)
        avg_lon = sum(c[1] for c in coords_list) / len(coords_list)

        # Create base map
        m = folium.Map(
            location=[avg_lat, avg_lon],
            zoom_start=zoom_start,
            tiles="OpenStreetMap",
            attr="OpenStreetMap contributors",
        )

        # Define colors for component types
        component_types = sorted(
            set(type(comp).__name__ for comp in components_with_coords)
        )
        type_color_map: dict[str, str] = {}
        color_palette = [
            "blue", "orange", "green", "red", "purple",
            "gray", "lightblue", "darkgray", "cadetblue", "darkgreen",
        ]
        for i, t in enumerate(component_types):
            type_color_map[t] = color_palette[i % len(color_palette)]

    # Add markers for each component
        for comp, (lat, lon) in zip(components_with_coords, coords_list):
            comp_type = type(comp).__name__
            color = type_color_map.get(comp_type, "cadetblue")

            if show_names:
                popup_html = f"<b>{comp.name}</b><br>Type: {comp_type}"
                tooltip_text = comp.name
            else:
                popup_html = comp_type
                tooltip_text = comp_type

            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=tooltip_text,
                icon=folium.Icon(color=color, icon="info-sign", prefix="glyphicon"),
            ).add_to(m)

        # Draw connections (edges) between components
        for u, v in self.graph.edges:
            u_coords: tuple[float, float] | None = None
            v_coords: tuple[float, float] | None = None

            if u.coords is not None:
                if isinstance(u.coords, tuple) and len(u.coords) == 2:
                    u_coords = (u.coords[0], u.coords[1])
                elif isinstance(u.coords, list) and len(u.coords) > 0:
                    u_coords = (u.coords[0][0], u.coords[0][1])

            if v.coords is not None:
                if isinstance(v.coords, tuple) and len(v.coords) == 2:
                    v_coords = (v.coords[0], v.coords[1])
                elif isinstance(v.coords, list) and len(v.coords) > 0:
                    v_coords = (v.coords[0][0], v.coords[0][1])

            if u_coords is None or v_coords is None:
                continue

            # Determine line color based on component types
            if show_types:
                u_type = type(u).__name__
                v_type = type(v).__name__
                u_color = type_color_map.get(u_type, "gray")
                v_color = type_color_map.get(v_type, "gray")
                line_color = u_color if u_color == v_color else "gray"
            else:
                line_color = "#555555"

            # Build line coordinates
            line_coords: list[tuple[float, float]] = [u_coords, v_coords]

            if isinstance(u.coords, list) and len(u.coords) > 1:
                line_coords = [(c[0], c[1]) for c in u.coords] + [v_coords]
            elif isinstance(v.coords, list) and len(v.coords) > 1:
                line_coords = [u_coords] + [(c[0], c[1]) for c in v.coords]

            popup_html = f"Connection: {u.name} &harr; {v.name}" if show_names else None
            folium.PolyLine(
                locations=line_coords,
                weight=2,
                color=line_color,
                opacity=0.7,
                popup=popup_html,
            ).add_to(m)

        # Add legend if enabled
        if show_types and component_types:
            legend_items = "".join(
                f'<i class="fa fa-circle" style="color:{type_color_map.get(t, "gray")}"></i> {t}<br>'
                for t in component_types
            )
            legend_html = (
                '<div style="position:fixed;bottom:50px;right:50px;'
                'width:150px;border:2px solid grey;z-index:9999;'
                'font-size:12px;background-color:white;'
                'padding:10px;border-radius:5px;opacity:0.9;">'
                f"<b>Component Types</b><br>{legend_items}</div>"
            )
            m.get_root().html.add_child(folium.Element(legend_html))

        # Add fullscreen option
        plugins.Fullscreen(
            position="topleft",
            title="Enter fullscreen",
            title_cancel="Exit fullscreen",
            force_separate_button=True,
        ).add_to(m)

        # Export map - part 1 of 2
        if export_path is not None:
            # Save as HTML first
            if export_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                html_path = export_path.rsplit(".", 1)[0] + ".html"
            else:
                html_path = export_path if export_path.endswith(".html") else export_path + ".html"

            m.save(html_path)
            Logger.log_to_selected(f"OSM map saved as HTML: {html_path}")

            # Attempt image export via selenium if image format requested
            if export_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                try:
                    from selenium import webdriver
                    from selenium.webdriver.chrome.options import Options
                    import time
                    import os

                    chrome_options = Options()
                    chrome_options.add_argument("--headless")
                    chrome_options.add_argument("--disable-gpu")
                    chrome_options.add_argument("--no-sandbox")
                    chrome_options.add_argument("--disable-dev-shm-usage")
                    chrome_options.add_argument("--window-size=1920,1080")

                    try:
                        driver = webdriver.Chrome(options=chrome_options)
                    except Exception:
                        Logger.log_to_selected(
                            "Chrome/ChromeDriver not available for image export. "
                            "Map saved as HTML instead. "
                            "Install Chrome and ChromeDriver to enable image export."
                        )
                        return html_path

                    driver.get(f"file://{os.path.abspath(html_path)}")
                    time.sleep(3)  # Wait for map tiles to load

                    driver.save_screenshot(export_path)
                    driver.quit()

                    Logger.log_to_selected(f"OSM map image saved to: {export_path}")
                    return None

                except ImportError:
                    Logger.log_to_selected(
                        "Selenium not installed. Map saved as HTML. "
                        "Install selenium for image export: pip install selenium"
                    )
                    return html_path
                except Exception as e:
                    Logger.log_to_selected(
                        f"Error exporting map image: {e}. "
                        "Map saved as HTML instead."
                    )
                    return html_path

            return None
        else:
            # Return HTML representation
            return m._repr_html_()

    pass  # Placeholder


def _get_class(full_class_name: str) -> type[Component]:
    split_name = full_class_name.split(".")
    module_name = ".".join(split_name[:-1])
    class_name = split_name[-1]
    module = importlib.import_module(module_name)
    return getattr(module, class_name)
