from qgis.PyQt.QtCore import Qt, QSettings, QTranslator, QCoreApplication, QVariant
from qgis.PyQt.QtGui import QIcon, QCursor, QColor
from qgis.PyQt.QtWidgets import QAction, QInputDialog
from qgis.core import QgsProject, QgsVectorLayer, QgsFeature, QgsRectangle, QgsGeometry, QgsPointXY, QgsFields, QgsField, QgsGeometryUtils, QgsLineSymbol, QgsFillSymbol, QgsDistanceArea, QgsUnitTypes, QgsSpatialIndex, QgsCoordinateReferenceSystem
from qgis.utils import iface
from qgis.core import Qgis

from .resources import *
from .route_tracking_dialog import route_trackingDialog
import os.path

from .gtfs_db import Database
from .stops_layer import StopsLayer
from .pedestrian_graph import PedestrianGraph
from .route_graph import RouteGraph
from .utils import change_style_layer

from collections import defaultdict
from itertools import islice
import networkx as nx
import osmnx as ox
import pprint as pp
import geopandas as gpd
import datetime

DISTANCE = 1000
DISTANCE_EDGE = 50

class Analysis:
    def get_integer_from_user(self):
        """Get stop ID from user"""

        stop_id, check = QInputDialog.getText(None, "Insert the ID of the stop that you want to analyse", "Stop ID:")

        if check:
            if stop_id == "":
                # Error message
                iface.messageBar().pushMessage("Error", "You have to insert a stop ID", level=Qgis.Critical, duration=5)
                return self.get_integer_from_user()
            
            database = Database()
            stop_info = database.select_stop_coordinates_by_id(stop_id)

            if stop_info:
                return stop_id, stop_info[0]
            else:
                iface.messageBar().pushMessage("Error", "Stop ID not found, try another one", level=Qgis.Critical, duration=5)
                return self.get_integer_from_user()
        else:
            return None, None
            
    def show_nearby_stops(self):
        """Get nearby stops"""

        LAYER_NAME_STOPS = "stops"
        LAYER_NAME_BUFFER = "circular_buffer"
        LAYER_NAME_SELECTED_STOPS = "selected_stops"
        LAYER_NAME_DISCARDED_STOPS = "discarded_stops"
        LAYER_NAME_SHORTEST_PATHS = "shortest_paths"
        LAYER_NAME_STARTING_POINT = "starting_point"
        GRAPH_PATH_GML = self._path + "/graphs/pedestrian_graph.graphml"

        # check if the layer is already present. If is present, delete it
        project = QgsProject.instance()
        if project.mapLayersByName(LAYER_NAME_SELECTED_STOPS):
            project.removeMapLayer(project.mapLayersByName(LAYER_NAME_SELECTED_STOPS)[0])
        if project.mapLayersByName(LAYER_NAME_BUFFER):
            project.removeMapLayer(project.mapLayersByName(LAYER_NAME_BUFFER)[0])
        if project.mapLayersByName(LAYER_NAME_DISCARDED_STOPS):
            project.removeMapLayer(project.mapLayersByName(LAYER_NAME_DISCARDED_STOPS)[0])
        if project.mapLayersByName(LAYER_NAME_SHORTEST_PATHS):
            project.removeMapLayer(project.mapLayersByName(LAYER_NAME_SHORTEST_PATHS)[0])
        if project.mapLayersByName(LAYER_NAME_STARTING_POINT):
            project.removeMapLayer(project.mapLayersByName(LAYER_NAME_STARTING_POINT)[0])

        # get stop ID from user
        current_stop_id, stop = self.get_integer_from_user()

        # check if the user has inserted a stop ID
        if current_stop_id is None and stop is None:
            return

        # get coordinates and the name of the stop
        x_coord = stop[1]
        y_coord = stop[0]
        current_stop_name = stop[2]

        # get the transports of the stop
        database = Database()
        current_stop_transports = database.select_transports_by_stop_id(current_stop_id)
        current_stop_transports_list = [transport[0] for transport in current_stop_transports]

        # obtain stops layer and crs
        stops_layer = project.mapLayersByName(LAYER_NAME_STOPS)[0]
        crs = stops_layer.crs()

        # create starting point
        starting_point = QgsPointXY(x_coord, y_coord)

        # create geometry for the starting point
        starting_point_geometry = QgsGeometry.fromPointXY(starting_point)

        # define fields for feature attributes
        fields = QgsFields()
        fields.append(QgsField("ID", QVariant.String))
        fields.append(QgsField("Stop_name", QVariant.String))

        # create and load layer for the starting point
        self.create_and_load_layer_starting_point(crs, fields, starting_point_geometry)

        # create and load layer for the circular buffer
        circular_buffer = self.create_and_load_layer_circular_buffer(crs, starting_point_geometry, stops_layer)

        # create and load layer for the selected and discarded stops
        selected_stops = self.create_and_load_layer_selected_stops(crs, fields, stops_layer, circular_buffer, current_stop_transports_list, current_stop_id)

        # load pedestrian graph
        G_walk = ox.load_graphml(GRAPH_PATH_GML,
                            node_dtypes={'fid': int, 'osmid': str, 'x': float, 'y': float},
                            edge_dtypes={'fid': int, 'u': str, 'v': str, 'key': int, 'weight': float, 'transport': str, 'from': str, 'to': str})
        
        # get the nearest node of the starting point
        starting_point_nearest_node = ox.nearest_nodes(G_walk, x_coord, y_coord)

        # create a list with the information of the starting stop
        starting_stop_info = [current_stop_id, current_stop_name, starting_point_nearest_node]

        # create and load layer for the shortest paths
        self.create_and_load_layer_shortest_paths(crs, selected_stops, starting_stop_info, G_walk)

    def create_and_load_layer_starting_point(self, crs: QgsCoordinateReferenceSystem, fields: QgsFields, starting_point_geometry: QgsGeometry):
        """Create a layer to store the starting point and fill it with the starting point"""

        # create a layer to store the starting point
        starting_point_layer = QgsVectorLayer("Point?crs=" + crs.authid(), "starting_point", "memory")

        # add fields to the layer
        starting_point_layer.dataProvider().addAttributes(fields)

        # start editing the layer
        starting_point_layer.startEditing()

        # create a new feature
        new_feature = QgsFeature(starting_point_layer.fields())
        new_feature.setGeometry(starting_point_geometry)

        # add the feature to the layer
        starting_point_layer.addFeature(new_feature)

        # commit changes
        starting_point_layer.commitChanges()

        # change style of the layer
        change_style_layer(starting_point_layer, 'square', 'blue', '2', None)

        # load layer
        project = QgsProject.instance()
        project.addMapLayer(starting_point_layer)

    def create_and_load_layer_circular_buffer(self, crs: QgsCoordinateReferenceSystem, starting_point_geometry: QgsGeometry, stops_layer: QgsVectorLayer):
        """Create a layer to store the circular buffer and fill it with the circular buffer"""

        project = QgsProject.instance()

        # create distance area
        distance_area = QgsDistanceArea()
        distance_area.setSourceCrs(stops_layer.crs(), project.transformContext())
        distance_area.setEllipsoid(project.ellipsoid())

        # convert distance from meters to degrees
        distance_degrees = distance_area.convertLengthMeasurement(DISTANCE, QgsUnitTypes.DistanceUnit.Degrees)

        # create a circular buffer
        circular_buffer = starting_point_geometry.buffer(distance_degrees, segments=32)

        # create new feature to store the circular buffer
        circular_feature = QgsFeature()
        circular_feature.setGeometry(circular_buffer)

        # add the circular buffer to the layer
        circular_buffer_layer = QgsVectorLayer("Polygon?crs=" + crs.authid(), "circular_buffer", "memory")
        circular_buffer_layer.dataProvider().addFeatures([circular_feature])

        # change style of the layer
        fill_symbol = QgsFillSymbol.createSimple({'color': 'cyan', 'outline_color': 'black', 'outline_width': '0.5', 'style': 'solid'})
        fill_symbol.setColor(QColor(0, 255, 255, 80))
        circular_buffer_layer.renderer().setSymbol(fill_symbol)

        # load layer
        project.addMapLayer(circular_buffer_layer)

        return circular_buffer
        
    def create_and_load_layer_selected_stops(self, crs: QgsCoordinateReferenceSystem, fields: QgsFields, stops_layer: QgsVectorLayer, circular_buffer: QgsGeometry, current_stop_transports_list: list, current_stop_id: QgsGeometry):
        """Create a layer to store the selected stops and fill it with the selected stops"""

        selected_stops_dict = defaultdict(dict)

        database = Database()
        project = QgsProject.instance()
        
        # create a temporary new layer to store all the selected stops
        selected_stops_layer = QgsVectorLayer("Point?crs=" + crs.authid(), "selected_stops", "memory")
        discarded_stops_layer = QgsVectorLayer("Point?crs=" + crs.authid(), "discarded_stops", "memory")

        # add fields to the layer
        selected_stops_layer.dataProvider().addAttributes(fields)
        discarded_stops_layer.dataProvider().addAttributes(fields)

        # start editing the layer
        selected_stops_layer.startEditing()
        discarded_stops_layer.startEditing()

        # create a spatial index for the stops layer
        stops_index = QgsSpatialIndex(stops_layer.getFeatures())

        # find the features that intersect with the circular buffer
        intersecting_stop_ids = stops_index.intersects(circular_buffer.boundingBox())

        # iterate over the features that intersect with the circular buffer
        for stop_id in intersecting_stop_ids:
            # get the feature
            feature = stops_layer.getFeature(stop_id)
            stop_point = feature.geometry()
            
            selected_stop_transports = database.select_transports_by_stop_id(feature["ID"])
            selected_stop_transports_list = [transport[0] for transport in selected_stop_transports]

            # check if the stop is inside the circular buffer
            if circular_buffer.contains(stop_point):
                # create a new feature
                new_feature = QgsFeature(selected_stops_layer.fields())
                new_feature.setGeometry(stop_point)
                new_feature.setAttributes([feature["ID"], feature["Stop_name"]])

                # check if the intersected stop is the starting stop and don't add it to the layer
                if feature["ID"] != current_stop_id:
                    # check if the intersected stop has at least one transport in common with the starting stop
                    if set(current_stop_transports_list).intersection(set(selected_stop_transports_list)):
                        # add the feature to the layer
                        discarded_stops_layer.addFeature(new_feature)
                    else:
                        # add the feature to the layer
                        selected_stops_layer.addFeature(new_feature)
                        
                        # add the feature to the dictionary, the key is the point and the two values are the ID and the name of the stop
                        selected_stops_dict[stop_point] = [feature["ID"], feature["Stop_name"]]

        # commit changes
        selected_stops_layer.commitChanges()
        discarded_stops_layer.commitChanges()

        # change style of the layer
        change_style_layer(selected_stops_layer, 'square', 'yellow', '2', None)
        change_style_layer(discarded_stops_layer, 'square', 'red', '2', None)

        # load layer
        project.addMapLayer(selected_stops_layer)
        project.addMapLayer(discarded_stops_layer)

        print("Starting point transports: ", current_stop_transports_list)

        return selected_stops_dict

    def create_and_load_layer_shortest_paths(self, crs: QgsCoordinateReferenceSystem, selected_stops_dict: list, starting_stop_info: list, G_walk: nx.Graph):
        """Create a layer to store the shortest paths and fill it with the shortest paths"""

        # if selected_stops_dict is empty, return
        if not selected_stops_dict:
            print("No admitted stops found")
            return

        # create a layer to store the shortest paths
        shortest_paths_layer = QgsVectorLayer("LineString?crs=" + crs.authid(), "shortest_paths", "memory")

        # get the information of the starting stop
        starting_stop_id = starting_stop_info[0]
        starting_stop_name = starting_stop_info[1]
        starting_point_nearest_node = starting_stop_info[2]

        # define fields for feature attributes
        fields = QgsFields()
        fields.append(QgsField("From", QVariant.String))
        fields.append(QgsField("From_Stop_Name", QVariant.String))
        fields.append(QgsField("To", QVariant.String))
        fields.append(QgsField("To_Stop_Name", QVariant.String))
        fields.append(QgsField("Length", QVariant.Double))

        # add fields to the layer
        shortest_paths_layer.dataProvider().addAttributes(fields)

        # start editing the layer
        shortest_paths_layer.startEditing()

        for stop_key in selected_stops_dict:
            # get the coordinates of the selected stop
            stop = stop_key.asPoint()

            # get the ID and the name of the selected stop
            selected_stop_id = selected_stops_dict[stop_key][0]
            selected_stop_name = selected_stops_dict[stop_key][1]

            # get the nearest node of the selected stop
            stop_nearest_node = ox.nearest_nodes(G_walk, stop.x(), stop.y())

            # get the shortest path
            shortest_path = nx.shortest_path(G_walk, starting_point_nearest_node, stop_nearest_node, weight="length")

            # get the length of the shortest path
            shortest_paths_length = nx.shortest_path_length(G_walk, starting_point_nearest_node, stop_nearest_node, weight="length")

            # create a list of points with a list comprehension
            path_line = [QgsPointXY(G_walk.nodes[node]["x"], G_walk.nodes[node]["y"]) for node in shortest_path]

            # create a geometry
            path_geometry = QgsGeometry.fromPolylineXY(path_line)

            # create a new feature
            new_feature = QgsFeature(shortest_paths_layer.fields())
            new_feature.setGeometry(path_geometry)
            new_feature.setAttributes([starting_stop_id, starting_stop_name, selected_stop_id, selected_stop_name, shortest_paths_length])

            # add the feature to the layer
            shortest_paths_layer.addFeature(new_feature)

        # commit changes
        shortest_paths_layer.commitChanges()

        # change style of the layer
        change_style_layer(shortest_paths_layer, None, 'black', None, '0.5')

        # load layer
        project = QgsProject.instance()
        project.addMapLayer(shortest_paths_layer)