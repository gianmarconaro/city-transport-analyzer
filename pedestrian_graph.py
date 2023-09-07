from qgis.core import QgsProject, QgsVectorLayer

from .resources import *
from shapely.geometry import Polygon
import os.path

from .utils import change_style_layer

import osmnx as ox

class PedestrianGraph:
    def create_pedestrian_layer(self):
        """Create a layer with pedestrian"""

        POLYGON_PATH = self._path + "/polygons/milan_walk.txt"
        GRAPH_PATH_GPKG = self._path + "/graphs/pedestrian_graph.gpkg"
        GRAPH_PATH_GML = self._path + "/graphs/pedestrian_graph.graphml"
        GRAPH_NAME = "pedestrian_graph"
        
        project = QgsProject.instance()
        
        if os.path.exists(GRAPH_PATH_GPKG):
            if project.mapLayersByName(GRAPH_NAME):
                return
            else:
                self.load_pedestrian_layer(GRAPH_PATH_GPKG, GRAPH_NAME)
                return

        print("Creating pedestrian graph...")

        # read the polygon coordinates from the file
        polygon_points = []
        with open(POLYGON_PATH, "r") as file:
            for line in file:
                line = line.strip()
                if line:
                    line = line.split(",")
                    polygon_points.append((float(line[0]), float(line[1])))

        # import from osmnx the graph of the city with pedestrian network
        polygon = Polygon(polygon_points)
        pedestrian_graph = ox.graph_from_polygon(polygon, network_type="walk")

        # import and save it as a layer
        ox.save_graph_geopackage(pedestrian_graph, filepath=GRAPH_PATH_GPKG, directed=False)
        ox.save_graphml(pedestrian_graph, filepath=GRAPH_PATH_GML)

        print("Pedestrian graph created!")

        # load layer
        self.load_pedestrian_layer(GRAPH_PATH_GPKG, GRAPH_NAME)

    def load_pedestrian_layer(self, layer_path: str, layer_name: str):
        """Load pedestrian layer"""

        print("Loading pedestrian graph...")

        project = QgsProject.instance()
        layer = QgsVectorLayer(layer_path + "|layername=edges", layer_name, "ogr")
        if not layer.isValid():
            print("Layer failed to load!")
        else:
            # Add layer to the registry
            print("Pedestrian graph loaded!")
            project.addMapLayer(layer)
        
        # change style of the layer
        change_style_layer(layer, None, 'darkgreen', None, '0.5')