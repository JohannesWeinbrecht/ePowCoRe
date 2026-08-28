import json
import os
import pathlib
import time

from epowcore.power_factory.power_factory_converter import PFModel, PowerFactoryConverter

PATH = pathlib.Path(__file__).parent.resolve()


def main():
    model_name = "Nine-bus System"

    start = time.perf_counter()

    model = PFModel("Nine-bus System", "01- Load Flow", 60)
    converter = PowerFactoryConverter()
    result = converter.to_gdf(
        model=model,
        log_path=str(PATH.parent / f"pf_{model_name}.log"),
        create_mapping=True,
        add_get_mapping=True,
        auto_convert=True,
    )

    print(result)

    print(f"conversion took {time.perf_counter() - start:.1f}s")

    ## IMPORT JSON FILE TO CHECK MODEL CONSISTENCY
    # with open(f"tests/out/{model_name}_gdf.json", "r", encoding="utf-8") as file:
    #     data_str = file.read()
    # data = json.loads(data_str)
    # core_model = CoreModel.import_dict(data)

    # print(data_str)
    # visualize_graph(core_model.graph)


if __name__ == "__main__":
    main()
