import json
import os
import pathlib
import time
import networkx as nx
import pandas as pd
from matplotlib import pyplot as plt
import pandapower as pp

from epowcore.gdf.core_model import CoreModel
from epowcore.pandapower.pandapower_converter import PandapowerConverter

PATH = pathlib.Path(__file__).parent.resolve()


def main() -> None:
    model_name = "steigwegOberderdingenFixed1"

    start = time.perf_counter()

    with open(PATH.parent / "steigwegOberderdingenTest1_gdf.json", "r", encoding="utf-8") as file:
        data_str = file.read()
        data = json.loads(data_str)
        core_model = CoreModel.import_dict(data)
        print(core_model)

        internal_graph = core_model.graph.get_internal_graph()
        nx.draw_networkx(internal_graph, node_size=0.1, with_labels=True)
        plt.show()

        converter = PandapowerConverter(debug=False)
        pandapower_model = converter.from_gdf(
            core_model, f"{model_name}", log_path=str(PATH.parent / "pandapower.log")
        )

        pp.plotting.simple_plot(pandapower_model.network, bus_size=0.1)
        plt.show()
        # pp.plotting.plotly.simple_plotly(net=pandapower_model.network)
        pp.diagnostic(pandapower_model.network)
        pp.runpp(pandapower_model.network)

        # Create directory if it does not exist
        if not os.path.exists("output/pandapower"):
            os.makedirs("output/pandapower")
        converter.write_to_pandapower_json(
            model=pandapower_model, filepath=f"output/pandapower/{model_name}.json"
        )
        with pd.option_context(
            "display.max_rows", None, "display.max_columns", None
        ):  # more options can be specified also
            print(pandapower_model.network.bus)

        print(f"conversion took {time.perf_counter() - start:.1f}s")


if __name__ == "__main__":
    main()
