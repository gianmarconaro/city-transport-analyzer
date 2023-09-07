from qgis.core import QgsProject, QgsVectorLayer

from .resources import *
from shapely.geometry import Polygon
import os.path

from .utils import change_style_layer

import osmnx as ox

class DriveGraph:
    def create_drive_layer(self):
        """Create a layer with drive graph"""

        POLYGON_PATH = self._path + "/polygons/milan_walk.txt"
        GRAPH_PATH_GPKG = self._path + "/graphs/drive_graph.gpkg"
        GRAPH_PATH_GML = self._path + "/graphs/drive_graph.graphml"
        GRAPH_NAME = "drive_graph"
        
        project = QgsProject.instance()
        
        if os.path.exists(GRAPH_PATH_GPKG):
            if project.mapLayersByName(GRAPH_NAME):
                return
            else:
                self.load_drive_layer(GRAPH_PATH_GPKG, GRAPH_NAME)
                return

        print("Creating drive graph...")

        # read the polygon coordinates from the file
        polygon_points = []
        with open(POLYGON_PATH, "r") as file:
            for line in file:
                line = line.strip()
                if line:
                    line = line.split(",")
                    polygon_points.append((float(line[0]), float(line[1])))

        # import from osmnx the graph of the city with drive network
        polygon = Polygon(polygon_points)
        drive_graph = ox.graph_from_polygon(polygon, network_type="drive")

        # import and save it as a layer
        ox.save_graph_geopackage(drive_graph, filepath=GRAPH_PATH_GPKG, directed=False)
        ox.save_graphml(drive_graph, filepath=GRAPH_PATH_GML)

        print("Drive graph created!")

        # load layer
        self.load_drive_layer(GRAPH_PATH_GPKG, GRAPH_NAME)

    def load_drive_layer(self, layer_path: str, layer_name: str):
        """Load drive layer"""

        print("Loading drive graph...")

        project = QgsProject.instance()
        layer = QgsVectorLayer(layer_path + "|layername=edges", layer_name, "ogr")
        if not layer.isValid():
            print("Layer failed to load!")
        else:
            # Add layer to the registry
            print("Drive graph loaded!")
            project.addMapLayer(layer)
        
        # change style of the layer
        change_style_layer(layer, None, 'black', None, '0.5')