from qgis.core import QgsProject, QgsVectorLayer, QgsWkbTypes, QgsMapLayer, QgsGeometry, QgsPointXY
from qgis.PyQt.QtWidgets import QProgressDialog, QApplication

from .resources import *
from shapely.geometry import Polygon
import os.path

from .utils import change_style_layer

import osmnx as ox

class PedestrianGraph:
    def create_pedestrian_layer(self, selected_polygon_layer: str):
        """Create a layer with pedestrian"""

        # POLYGON_PATH = self._path + "/shapefiles/Test_ososo.shp"
        GRAPH_PATH_GPKG = self._path + "/graphs/pedestrian_graph.gpkg"
        GRAPH_PATH_GML = self._path + "/graphs/pedestrian_graph.graphml.xml"
        GRAPH_NAME = "pedestrian_graph"

        project = QgsProject.instance()

        if os.path.exists(GRAPH_PATH_GPKG):
            if project.mapLayersByName(GRAPH_NAME):
                return
            else:
                self.load_pedestrian_layer(GRAPH_PATH_GPKG, GRAPH_NAME)
                return
            
        # get the selected polygon layer by name
        polygon_layer = QgsProject.instance().mapLayersByName(selected_polygon_layer)[0]
        polygon = self.polygon_from_polygon_layer(polygon_layer)

        # create a window to alert the user that the plugin is working and mantain the window open until the plugin is finished
        progressMessageBar = QProgressDialog()
        progressMessageBar.setLabelText("Creating pedestrian graph...")
        progressMessageBar.setWindowModality(2)
        progressMessageBar.setCancelButtonText(None)
        progressMessageBar.setMinimum(0)
        progressMessageBar.setMaximum(100)
        progressMessageBar.setWindowModality(2)
        progressMessageBar.setValue(0)
        progressMessageBar.show()
        QApplication.processEvents()

        print("Creating pedestrian graph...")
        
        # # read the polygon coordinates from the file
        # polygon_points = []
        # with open(POLYGON_PATH, "r") as file:
        #     for line in file:
        #         line = line.strip()
        #         if line:
        #             line = line.split(",")
        #             polygon_points.append((float(line[0]), float(line[1])))

        # polygon = Polygon(polygon_points)

        progressMessageBar.setValue(20)

        pedestrian_graph = ox.graph_from_polygon(polygon, network_type="walk")

        ox.save_graph_geopackage(
            pedestrian_graph, filepath=GRAPH_PATH_GPKG, directed=False
        )
        ox.save_graphml(pedestrian_graph, filepath=GRAPH_PATH_GML)

        print("Pedestrian graph created!")

        progressMessageBar.setValue(100)

        self.load_pedestrian_layer(GRAPH_PATH_GPKG, GRAPH_NAME)

    def load_pedestrian_layer(self, layer_path: str, layer_name: str):
        """Load pedestrian layer"""

        print("Loading pedestrian graph...")

        project = QgsProject.instance()
        layer = QgsVectorLayer(layer_path + "|layername=edges", layer_name, "ogr")
        if not layer.isValid():
            print("Layer failed to load!")
        else:
            print("Pedestrian graph loaded!")
            project.addMapLayer(layer)

        change_style_layer(layer, None, "darkgreen", None, "0.5")

    
    def polygon_from_polygon_layer(self, polygon_layer):
        # extract the polygon from the layer
        geometry = polygon_layer.getFeature(0).geometry()

        # multipolygon cannot be converted to polygon, so we do it like this
        multi_polygon = geometry.asMultiPolygon()  # This returns a list of polygons, each polygon is a list of rings

        # Check if there is at least one polygon
        if len(multi_polygon) > 0:
            # Extract the first polygon (first element of the first list)
            # Each polygon is a list where the first element is the outer ring and subsequent elements are holes
            first_polygon = multi_polygon[0][0]  # This is the outer boundary of the first polygon

            # If you need to create a new QgsGeometry object from this outer ring
            single_polygon_geometry = QgsGeometry.fromPolygonXY([first_polygon])
            print("Single Polygon Geometry:", single_polygon_geometry)
        else:
            print("No polygons available in the MultiPolygon.")

        # get the polygon coordinates
        polygon = Polygon([QgsPointXY(point) for point in first_polygon])

        return polygon
