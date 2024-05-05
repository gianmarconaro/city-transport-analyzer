import os.path

from qgis.core import (
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import QVariant

from .gtfs_db import Database
from .utils import change_style_layer
from .resources import *


class StopsLayer:
    def create_stops_layer(self):
        """Create a layer with stops"""

        if not os.path.exists(self._path + "/shapefiles"):
            os.makedirs(self._path + "/shapefiles")

        STOPS_LAYER_PATH = self._path + "/shapefiles/stops.shp"
        STOPS_LAYER_NAME = "stops"

        project = QgsProject.instance()
        crs = project.crs()

        if os.path.exists(STOPS_LAYER_PATH):
            if project.mapLayersByName(STOPS_LAYER_NAME):
                return
            else:
                self.load_stops_layer(STOPS_LAYER_PATH, STOPS_LAYER_NAME)
                return

        print("Creating stops layer...")

        database = Database()
        stops = database.select_all_coordinates_stops()

        # define fields for feature attributes
        fields = QgsFields()
        fields.append(QgsField("ID", QVariant.String))
        fields.append(QgsField("Stop_name", QVariant.String))
        fields.append(QgsField("Lon", QVariant.Double))
        fields.append(QgsField("Lan", QVariant.Double))
        # fields.append(QgsField("Transports", QVariant.String)) # the cost is too high

        writer = QgsVectorFileWriter(
            STOPS_LAYER_PATH, "UTF-8", fields, QgsWkbTypes.Point, crs, "ESRI Shapefile"
        )

        if writer.hasError() != QgsVectorFileWriter.NoError:
            print("Error when creating shapefile: ", writer.errorMessage())

        for stop in stops:
            # stop information
            stop_id, stop_name, lat, lon = stop
            x_coord = float(lon)
            y_coord = float(lat)

            feature = QgsFeature()
            feature.setAttributes([stop_id, stop_name, lon, lat])

            point = QgsPointXY(x_coord, y_coord)
            geometry = QgsGeometry.fromPointXY(point)
            feature.setGeometry(geometry)

            writer.addFeature(feature)

        # select transports passing by the stop
        # transports = database.select_transports_by_stop_id(stop_id)
        # transports_list = [transport[0] for transport in transports]
        # transports_string = ", ".join(transports_list)

        # takes all the stop id and then make a query to retrieve short name of the transport passing by all the stops id
        # result[0] -> stop_id
        # result[1] -> short_name

        del writer

        self.load_stops_layer(STOPS_LAYER_PATH, STOPS_LAYER_NAME)

        print("Stops layer created!")

    def load_stops_layer(self, layer_path: str, layer_name: str):
        """Load stops layer"""

        project = QgsProject.instance()
        layer = QgsVectorLayer(layer_path, layer_name, "ogr")
        if not layer.isValid():
            print("Layer failed to load!")
        else:
            project.addMapLayer(layer)

        change_style_layer(layer, "square", "green", "2", None)
