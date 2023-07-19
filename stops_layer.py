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

        # Create stops layer only if not present in shapefiles folder
        if os.path.exists(self._path + "/shapefiles/stops.shp"):
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
        fields.append(QgsField("Wheelchair_boarding", QVariant.Int))

        # define name and path
        layer_name = "stops"
        layer_path = self._path + "/shapefiles/stops.shp"
        project = QgsProject.instance()
        crs = project.crs()

        # define writer
        writer = QgsVectorFileWriter(
            layer_path, "UTF-8", fields, QgsWkbTypes.Point, crs, "ESRI Shapefile"
        )

        if writer.hasError() != QgsVectorFileWriter.NoError:
            print("Error when creating shapefile: ", writer.errorMessage())

        for stop in stops:
            # stop information
            stop_id = stop[0]
            stop_name = stop[1]
            lon = stop[3]
            lat = stop[2]
            wheelchair_boarding = stop[4]

            # add a feature with geometry
            fet = QgsFeature()
            fet.setAttributes([stop_id, stop_name, lon, lat, wheelchair_boarding])

            # create geometry
            point = QgsPointXY(stop[3], stop[2])
            geometry = QgsGeometry.fromPointXY(point)
            fet.setGeometry(geometry)

            # add the geometry to the layer
            writer.addFeature(fet)

        # takes all the stop id and then make a query to retrieve short name of the transport passing by all the stops id
        # result[0] -> stop_id
        # result[1] -> short_name

        # delete the writer to flush features to disk
        del writer

        # load layer
        self.load_stops_layer(layer_path, layer_name)

        # retrieve layer
        layer = project.mapLayersByName(layer_name)[0]

        # set layer style
        change_style_layer(layer, "square", "green", "2", None)

        print("Stops layer created!")

    def load_stops_layer(self, layer_path: str, layer_name: str):
        """Load stops layer"""

        project = QgsProject.instance()
        layer = QgsVectorLayer(layer_path, layer_name, "ogr")
        if not layer.isValid():
            print("Layer failed to load!")
        else:
            # Add layer to the registry
            project.addMapLayer(layer)
