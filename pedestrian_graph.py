from qgis.core import QgsProject, QgsVectorLayer

from .resources import *
from shapely.geometry import Polygon
import os.path

from .utils import change_style_layer

import osmnx as ox

class PedestrianGraph:
    def create_pedestrian_layer(self):
        """Create a layer with pedestrian"""

        GRAPH_PATH_GPKG = self._path + "/graphs/pedestrian_graph.gpkg"
        GRAPH_PATH_GML = self._path + "/graphs/pedestrian_graph.graphml"
        GRAPH_NAME = "pedestrian_graph"
        
        project = QgsProject.instance()
        
        if os.path.exists(GRAPH_PATH_GPKG):
            if project.mapLayersByName(GRAPH_NAME)[0]:
                return
            else:
                self.load_pedestrian_layer(GRAPH_PATH_GPKG, GRAPH_NAME)
                return

        print("Creating pedestrian graph...")

        # import from osmnx the graph of the city with pedestrian network
        polygon_points = [
            (9.0238440, 45.5688049),
            (8.9710258, 45.4870880),
            (9.0362519, 45.3998993),
            (9.1028265, 45.3989563),
            (9.1295947, 45.3902813),
            (9.1337597, 45.3627622),
            (9.1584220, 45.3437511),
            (9.1996759, 45.3243918),
            (9.2368805, 45.3498770),
            (9.2744939, 45.3779765),
            (9.3200069, 45.3726497),
            (9.3003535, 45.4105670),
            (9.3255021, 45.4171292),
            (9.3230602, 45.4256236),
            (9.3216027, 45.4377581),
            (9.3191024, 45.4569688),
            (9.3171787, 45.4801436),
            (9.3405980, 45.5006416),
            (9.4480864, 45.5395994),
            (9.4410152, 45.5515979),
            (9.3051172, 45.5385289),
            (9.2887717, 45.5485106),
            (9.2623524, 45.5608352),
            (9.2086188, 45.5747672),
            (9.2154706, 45.6200412),
            (9.2072581, 45.6359909),
            (9.1835785, 45.6331116),
            (9.1715159, 45.5687498),
            (9.1510879, 45.6013230),
            (9.1202015, 45.6285664),
            (9.1080186, 45.6211268),
            (9.1071606, 45.6003626),
            (9.1331555, 45.5931492),
            (9.1400191, 45.5850444),
            (9.1413918, 45.5653480),
            (9.0935889, 45.5606976),
            (9.0690415, 45.5772390),
            (9.0561722, 45.5741765),
            (9.0238440, 45.5688049),
        ]
        polygon = Polygon(polygon_points)
        place_name = "Milano, Lombardia, Italia"
        # place_name = "Madrid, Spain"
        # place_name = "Los Angeles, California, USA"
        # place_name = "Turin, Piedmont, Italy"
        pedestrian_graph = ox.graph_from_polygon(polygon, network_type="walk")
        # pedestrian_graph = ox.graph_from_place(place_name, network_type="walk")

        # define name and path
        layer_name = "pedestrian_graph"

        # import and save it as a layer
        ox.save_graph_geopackage(pedestrian_graph, filepath=GRAPH_PATH_GPKG, directed=False)
        ox.save_graphml(pedestrian_graph, filepath=GRAPH_PATH_GML)

        print("Pedestrian graph created!")

        # load layer
        self.load_pedestrian_layer(GRAPH_PATH_GPKG, layer_name)

        # change style of the layer
        layer = project.mapLayersByName(layer_name)[0]
        change_style_layer(layer, None, 'red', None, '0.5')

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