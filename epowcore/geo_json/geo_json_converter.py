from geojson import FeatureCollection

from epowcore.gdf.core_model import CoreModel
from epowcore.generic.constants import Platform
from epowcore.generic.converter_base import ConverterBase
from epowcore.geo_json.from_gdf.geo_json_export import export_geo_json


class GeoJSONConverter(ConverterBase[FeatureCollection]):
    platform = Platform.GEOJSON

    def _export(self, core_model: CoreModel, name: str) -> FeatureCollection:
        return export_geo_json(core_model)

    def _import(self, model: FeatureCollection) -> CoreModel:
        raise NotImplementedError()
