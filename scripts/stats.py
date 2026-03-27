import json
import pathlib
import networkx as nx
from matplotlib import pyplot as plt

from epowcore.gdf.bus import Bus
from epowcore.gdf.core_model import CoreModel
from epowcore.gdf.exciters.exciter import Exciter
from epowcore.gdf.generators.static_generator import StaticGenerator
from epowcore.gdf.generators.synchronous_machine import SynchronousMachine
from epowcore.gdf.governors.governor import Governor
from epowcore.gdf.load import Load
from epowcore.generic.tools.visualization import visualize_graph
from epowcore.gdf.power_system_stabilizers.power_system_stabilizer import PowerSystemStabilizer
from epowcore.gdf.pv_system import PVSystem
from epowcore.gdf.shunt import Shunt
from epowcore.gdf.tline import TLine
from epowcore.gdf.transformers.three_winding_transformer import ThreeWindingTransformer
from epowcore.gdf.transformers.two_winding_transformer import TwoWindingTransformer
from epowcore.gdf.voltage_source import VoltageSource


PATH = pathlib.Path(__file__).parent.resolve()


def main():
    with open("steigwegOberderdingenTest1_gdf.json", "r", encoding="utf-8") as file:
        data_str = file.read()
    data = json.loads(data_str)
    model = CoreModel.import_dict(data)

    nx_graph = model.graph.get_internal_graph()
    nx.draw_networkx(nx_graph, with_labels=False, node_size=100)
    plt.show()
    # print("Connected Components")
    # print(list(nx.connected_components(nx_graph)))
    print(f"Amount of connected components: {len(list(nx.connected_components(nx_graph)))}")

    print("=====")
    print("Graph")
    print("=====")
    print(f"Nodes:        {len(model.graph.nodes)}")
    print(f"Edges:        {len(model.graph.edges)}")
    print("")
    print("Components")
    print("==========")
    print(f"Buses:        {len(model.type_list(Bus))}")
    print("---")
    print(f"Lines:        {len(model.type_list(TLine))}")
    print(f"2-Wdg Trafos: {len(model.type_list(TwoWindingTransformer))}")
    print(f"3-Wdg Trafos: {len(model.type_list(ThreeWindingTransformer))}")
    print("---")
    print(f"Loads:        {len(model.type_list(Load))}")
    print(f"Shunts:       {len(model.type_list(Shunt))}")
    print("---")
    print(f"Generators:   {len(model.type_list(SynchronousMachine))}")
    print(f"Governors:    {len(model.type_list(Governor))}")
    print(f"Exciters:     {len(model.type_list(Exciter))}")
    print(f"PSSs:         {len(model.type_list(PowerSystemStabilizer))}")
    print("---")
    print(f"V-Sources:    {len(model.type_list(VoltageSource))}")
    print(f"Static Gen:   {len(model.type_list(StaticGenerator))}")
    print(f"PV systems:   {len(model.type_list(PVSystem))}")


if __name__ == "__main__":
    main()
