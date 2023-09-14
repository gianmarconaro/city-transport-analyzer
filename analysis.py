from qgis.PyQt.QtCore import Qt, QSettings, QTranslator, QCoreApplication, QVariant
from qgis.PyQt.QtGui import QIcon, QCursor, QColor, QIntValidator
from qgis.PyQt.QtWidgets import QAction, QInputDialog, QLineEdit, QDialog, QVBoxLayout, QLabel, QCheckBox, QPushButton, QDialogButtonBox
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
from .utils import change_style_layer, route_type_to_speed

from collections import defaultdict, deque
import networkx as nx
import osmnx as ox
import pprint as pp
import geopandas as gpd
import datetime

class Analysis:
    def error_manager(self, input, stop_info):
        # managing errors for stop ID
            if input[0] == "":
                # Error message
                iface.messageBar().pushMessage("Error", "You must insert a stop ID", level=Qgis.Critical, duration=5)
                return self.get_inputs()

            if not stop_info:
                iface.messageBar().pushMessage("Error", "Stop ID not found, try another one", level=Qgis.Critical, duration=5)
                return self.get_inputs()
            
            # managing errors for range
            if input[1] == "":
                # Error message
                iface.messageBar().pushMessage("Error", "You must insert a range", level=Qgis.Critical, duration=5)
                return self.get_inputs()
            
            # managing errors for time
            if input[2] == "":
                # Error message
                iface.messageBar().pushMessage("Error", "You must insert a time", level=Qgis.Critical, duration=5)
                return self.get_inputs()
            
    def get_inputs(self):
        """Get multiple input from user via dialog. One string input, two integer input and one checkbox"""
            
        # create a dialog
        dialog = QDialog()
        dialog.setWindowTitle("Analysis")

        # create a layout
        layout = QVBoxLayout()

        # create a label
        label = QLabel("Insert the ID of the stop that you want to analyse")
        layout.addWidget(label)

        # create a line edit
        self.stop_id_line_edit = QLineEdit()
        self.stop_id_line_edit.setPlaceholderText("Stop ID")
        layout.addWidget(self.stop_id_line_edit)

        # create a label
        label = QLabel("Insert the range of the analysis")
        layout.addWidget(label)

        # create a line edit
        self.range_line_edit = QLineEdit()
        self.range_line_edit.setPlaceholderText("Range (m) [100-2000]")
        self.range_line_edit.setValidator(QIntValidator(100, 2000))
        layout.addWidget(self.range_line_edit)

        # create a label
        label = QLabel("Insert the time of the analysis")
        layout.addWidget(label)

        # create a line edit
        self.time_line_edit = QLineEdit()
        self.time_line_edit.setPlaceholderText("Time (m) [5-20]")
        self.time_line_edit.setValidator(QIntValidator(5, 20))
        layout.addWidget(self.time_line_edit)

        # create a checkbox
        self.checkbox = QCheckBox("Detailed Analysis (May affect the performance of the application)")
        layout.addWidget(self.checkbox)

        # create a button box
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # set the layout
        dialog.setLayout(layout)

        # show the dialog
        result = dialog.exec_()

        if result == QDialog.Accepted:
            if self.range_line_edit.hasAcceptableInput() and self.time_line_edit.hasAcceptableInput():
                # get all the inputs
                input = [self.stop_id_line_edit.text(), self.range_line_edit.text(), self.time_line_edit.text()]

                database = Database()
                stop_info = database.select_stop_coordinates_by_id(input[0])

                # managing errors
                self.error_manager(input, stop_info)

                # get the input from the checkbox
                if self.checkbox.isChecked():
                    checkbox = True
                else:
                    checkbox = False

                return input, checkbox, stop_info[0]
            else:
                iface.messageBar().pushMessage("Error", "Range and time must be within the range", level=Qgis.Critical, duration=5)
                return self.get_inputs()
        else: return None, None, None

    # def get_stop_from_user(self):
    #     """Get stop ID from user"""

    #     stop_id, check = QInputDialog.getText(None, "Insert the ID of the stop that you want to analyse", "Stop ID:")

    #     if check:
    #         if stop_id == "":
    #             # Error message
    #             iface.messageBar().pushMessage("Error", "You must insert a stop ID", level=Qgis.Critical, duration=5)
    #             return self.get_stop_from_user()
            
    #         database = Database()
    #         stop_info = database.select_stop_coordinates_by_id(stop_id)

    #         if stop_info:
    #             range = self.get_range_from_user()
    #             if range:
    #                 time = self.get_time_from_user()
    #                 if time:
    #                     return stop_id, stop_info[0], range, time
    #                 else:
    #                     return None, None, None, None
    #             else:
    #                 return None, None, None, None
    #         else:
    #             iface.messageBar().pushMessage("Error", "Stop ID not found, try another one", level=Qgis.Critical, duration=5)
    #             return self.get_stop_from_user()
    #     else:
    #         iface.messageBar().pushMessage("Cancelled", "Operation cancelled", level=Qgis.Info, duration=5)
    #         return None, None, None, None
        
    # def get_range_from_user(self):
    #     """Get range from user"""

    #     range, check = QInputDialog.getInt(None, "Insert the range of the analysis", "Range (m):", 1000, 100, 2000, 100)

    #     if check:
    #         return range
    #     else:
    #         iface.messageBar().pushMessage("Cancelled", "Operation cancelled", level=Qgis.Info, duration=5)
    #         return None
        
    # def get_time_from_user(self):
    #     """Get time from user"""

    #     time, check = QInputDialog.getInt(None, "Insert the time of the analysis", "Time (m):", 10, 5, 20, 1)

    #     if check:
    #         return time
    #     else:
    #         iface.messageBar().pushMessage("Cancelled", "Operation cancelled", level=Qgis.Info, duration=5)
    #         return None
            
    def start_analysis(self):
        """Get nearby stops"""

        LAYER_NAME_STOPS = "stops"
        GRAPH_PATH_GML_WALK = self._path + "/graphs/pedestrian_graph.graphml"
        GRAPH_PATH_GML_ROUTE = self._path + "/graphs/routes_graph.graphml"

        # get the project
        project = QgsProject.instance()

        input, checkbox, stop = self.get_inputs()

        # check if the user has inserted a stop ID
        if input is None or checkbox is None:
            return
        
        current_stop_id = input[0]
        range = int(input[1])
        time = int(input[2])
        
        # remove layers
        self.remove_layers(project)

        # load pedestrian graph
        G_walk = ox.load_graphml(GRAPH_PATH_GML_WALK,
                            node_dtypes={'fid': int, 'osmid': str, 'x': float, 'y': float},
                            edge_dtypes={'fid': int, 'u': str, 'v': str, 'key': int, 'weight': float, 'transport': str, 'from': str, 'to': str})

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

        # load routes graph
        G = nx.read_graphml(GRAPH_PATH_GML_ROUTE)

        # create and load layer for the nearest starting point
        nearest_starting_point_node = self.create_and_load_nearest_starting_point(G, crs, fields, starting_point_geometry)

        # calculate reachable edges from the starting point
        self.create_and_load_layer_reachable_nodes(G, crs, nearest_starting_point_node, time, G_walk, checkbox)

        # create and load layer for the circular buffer
        circular_buffer = self.create_and_load_layer_circular_buffer(crs, starting_point_geometry, stops_layer, range)

        # create and load layer for the selected and discarded stops
        selected_stops = self.create_and_load_layer_selected_stops(crs, fields, stops_layer, circular_buffer, current_stop_transports_list, current_stop_id)
        
        # get the nearest node of the starting point
        starting_point_nearest_node = ox.nearest_nodes(G_walk, x_coord, y_coord)

        # create a list with the information of the starting stop
        starting_stop_info = [current_stop_id, current_stop_name, starting_point_nearest_node]

        # create and load layer for the shortest paths
        self.create_and_load_layer_shortest_paths(crs, selected_stops, starting_stop_info, G_walk)

        # find the intersections
        self.find_intersections()

    def remove_layers(self, project: QgsProject):
        """Remove layers from the project"""

        # layer names
        LAYER_NAME_BUFFER = "circular_buffer"
        LAYER_NAME_SELECTED_STOPS = "selected_stops"
        LAYER_NAME_DISCARDED_STOPS = "discarded_stops"
        LAYER_NAME_SHORTEST_PATHS = "shortest_paths"
        LAYER_NAME_STARTING_POINT = "starting_point"
        LAYER_NAME_STARTING_POINT_ROUTE = "starting_point_route"
        LAYER_NAME_SERVICE_AREA = "service_area"

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
        if project.mapLayersByName(LAYER_NAME_STARTING_POINT_ROUTE):
            project.removeMapLayer(project.mapLayersByName(LAYER_NAME_STARTING_POINT_ROUTE)[0])
        if project.mapLayersByName(LAYER_NAME_SERVICE_AREA):
            project.removeMapLayer(project.mapLayersByName(LAYER_NAME_SERVICE_AREA)[0])

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

    def create_and_load_nearest_starting_point(self, G: nx.MultiDiGraph, crs: QgsCoordinateReferenceSystem, fields: QgsFields, starting_point_geometry: QgsGeometry):
        """Create a layer to store the nearest starting point and fill it with the nearest starting point"""

        # calculate the nearest node of the starting point
        nearest_node = ox.nearest_nodes(G, starting_point_geometry.asPoint().x(), starting_point_geometry.asPoint().y())

        # get the coordinates of the nearest node
        nearest_node_x = G.nodes[nearest_node]["x"]
        nearest_node_y = G.nodes[nearest_node]["y"]

        # convert the node into a QgsPoint
        nearest_node_point = QgsPointXY(nearest_node_x, nearest_node_y)

        # load the point into a separate layer alone
        nearest_starting_point_layer = QgsVectorLayer("Point?crs=" + crs.authid(), "starting_point_route", "memory")

        # add fields to the layer
        nearest_starting_point_layer.dataProvider().addAttributes(fields)

        # start editing the layer
        nearest_starting_point_layer.startEditing()

        # create a new feature
        new_feature = QgsFeature(nearest_starting_point_layer.fields())
        new_feature.setGeometry(QgsGeometry.fromPointXY(nearest_node_point))

        # add the feature to the layer
        nearest_starting_point_layer.addFeature(new_feature)

        # commit changes
        nearest_starting_point_layer.commitChanges()

        # change style of the layer
        change_style_layer(nearest_starting_point_layer, 'square', 'blue', '2', None)

        # load layer
        project = QgsProject.instance()
        project.addMapLayer(nearest_starting_point_layer)

        return nearest_node

    def create_and_load_layer_circular_buffer(self, crs: QgsCoordinateReferenceSystem, starting_point_geometry: QgsGeometry, stops_layer: QgsVectorLayer, range: int):
        """Create a layer to store the circular buffer and fill it with the circular buffer"""

        project = QgsProject.instance()

        # create distance area
        distance_area = QgsDistanceArea()
        distance_area.setSourceCrs(stops_layer.crs(), project.transformContext())
        distance_area.setEllipsoid(project.ellipsoid())

        # convert distance from meters to degrees
        distance_degrees = distance_area.convertLengthMeasurement(range, QgsUnitTypes.DistanceUnit.Degrees)

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
        change_style_layer(shortest_paths_layer, None, 'orange', None, '0.5')

        # load layer
        project = QgsProject.instance()
        project.addMapLayer(shortest_paths_layer)

    def create_and_load_layer_reachable_nodes(self, G: nx.DiGraph, crs: QgsCoordinateReferenceSystem, starting_point: str, time_limit: int, G_walk: nx.Graph, checkbox: bool):
        """Calculate reachable edges in a time limit"""
    
        start_time = datetime.datetime.now()
        print("Starting time: ", start_time)

        # define a queue to store the nodes to visit
        queue = deque([(starting_point, 0)])
        reachable_edges = []
        visited_edges = set()

        # iterate over the queue
        while queue:
            current_node, time_elapsed = queue.popleft()
            # TODO: (1,2) aggiunto e poi (2,1) potrebbe riprenderlo, evita ció

            for _, end_node, edge_data in G.out_edges(current_node, data=True):
                if (current_node, end_node) not in visited_edges:
                    distance = edge_data["weight"] # meters
                    route_type = edge_data["route_type"] # km/h
                    transport = edge_data["transport"]

                    speed = route_type_to_speed(route_type)
                    travel_time = (distance / 1000) / speed * 60 # minutes

                    if time_elapsed + travel_time <= time_limit:
                        reachable_edges.append((current_node, end_node, distance, transport))
                        visited_edges.add((current_node, end_node))
                        queue.append((end_node, time_elapsed + travel_time))

        # load layer
        self.load_layer_reachable_edges(G, crs, reachable_edges, G_walk, checkbox)

    def load_layer_reachable_edges(self, G: nx.MultiDiGraph, crs: QgsCoordinateReferenceSystem, reachable_edges: list, G_walk: nx.Graph, checkbox: bool):
        """Create a layer to store the service area and fill it with the service area"""

        # if reachable_edges is empty, return
        if not reachable_edges:
            print("No reachable edges found")
            return

        # create a layer to store the service area
        service_area_layer = QgsVectorLayer("LineString?crs=" + crs.authid(), "service_area", "memory")

        # define fields for feature attributes
        fields = QgsFields()
        fields.append(QgsField("From", QVariant.String))
        fields.append(QgsField("To", QVariant.String))
        fields.append(QgsField("Weight", QVariant.Double))
        fields.append(QgsField("Transport", QVariant.String))

        # add fields to the layer
        service_area_layer.dataProvider().addAttributes(fields)

        # start editing the layer
        service_area_layer.startEditing()

        for edge in reachable_edges:
            # if the transport is walk, calculate the shortest path between the two nodes via pedestrian graph and add the edges to the service area
            if edge[3] == "walk" and checkbox:
                # calculate the nearest node of the starting point and of the ending point
                starting_point_nearest_node = ox.nearest_nodes(G_walk, G.nodes[edge[0]]["x"], G.nodes[edge[0]]["y"])
                ending_point_nearest_node = ox.nearest_nodes(G_walk, G.nodes[edge[1]]["x"], G.nodes[edge[1]]["y"])

                # get the shortest path
                shortest_path = nx.shortest_path(G_walk, starting_point_nearest_node, ending_point_nearest_node, weight="weight")

                # create a list of points with a list comprehension
                path_line = [QgsPointXY(G_walk.nodes[node]["x"], G_walk.nodes[node]["y"]) for node in shortest_path]

                # create a geometry
                edge_geometry = QgsGeometry.fromPolylineXY(path_line)

                # create a new feature
                new_feature = QgsFeature(service_area_layer.fields())
                new_feature.setGeometry(edge_geometry)
            else:
                # get the coordinates of the edge
                edge_coordinates = [(G.nodes[edge[0]]["x"], G.nodes[edge[0]]["y"]), (G.nodes[edge[1]]["x"], G.nodes[edge[1]]["y"])]

                # create QgsPoints 
                p1 = QgsPointXY(edge_coordinates[0][0], edge_coordinates[0][1])
                p2 = QgsPointXY(edge_coordinates[1][0], edge_coordinates[1][1])

                # create a geometry
                edge_geometry = QgsGeometry.fromPolylineXY([p1, p2])

            # create a new feature
            new_feature = QgsFeature(service_area_layer.fields())
            new_feature.setGeometry(edge_geometry)

            new_feature.setAttributes([edge[0], edge[1], edge[2], edge[3]])

            # add the feature to the layer
            service_area_layer.addFeature(new_feature)

        # commit changes
        service_area_layer.commitChanges()

        # change style of the layer
        change_style_layer(service_area_layer, None, 'lavander', None, '0.5')

        # load layer
        project = QgsProject.instance()
        project.addMapLayer(service_area_layer)





        # for edge in reachable_edges:
        #     # get the coordinates of the edge
        #     edge_coordinates = [(G.nodes[edge[0]]["x"], G.nodes[edge[0]]["y"]), (G.nodes[edge[1]]["x"], G.nodes[edge[1]]["y"])]

        #     # create QgsPoints 
        #     p1 = QgsPointXY(edge_coordinates[0][0], edge_coordinates[0][1])
        #     p2 = QgsPointXY(edge_coordinates[1][0], edge_coordinates[1][1])

        #     # create a geometry
        #     edge_geometry = QgsGeometry.fromPolylineXY([p1, p2])

        #     # create a new feature
        #     new_feature = QgsFeature(service_area_layer.fields())
        #     new_feature.setGeometry(edge_geometry)

        #     new_feature.setAttributes([edge[0], edge[1], edge[2], edge[3]])

        #     # add the feature to the layer
        #     service_area_layer.addFeature(new_feature)

        # # commit changes
        # service_area_layer.commitChanges()

        # # change style of the layer
        # change_style_layer(service_area_layer, None, 'lavander', None, '0.5')

        # # load layer
        # project = QgsProject.instance()
        # project.addMapLayer(service_area_layer)

    def find_intersections(self):
        # layer names 
        LAYER_NAME_DRIVE_GRAPH = "drive_graph"
        LAYER_NAME_SHORTEST_PATH = "shortest_paths"
        print("Intersections")

        project = QgsProject.instance()
        drive_graph_layer = project.mapLayersByName(LAYER_NAME_DRIVE_GRAPH)[0]
        service_area_layer = project.mapLayersByName(LAYER_NAME_SHORTEST_PATH)[0]

        # default dict to store the intersections
        intersections_dict = defaultdict(list)

        # calculate the intersections between the two layers and calculate how many times an edge is intersected and store also the name of the street. I wanna use the spatial index so I don't iterate over all the features and Is important to count how many times an edge is intersected and if an edge is intersected 0 times, it means that the edge is not inside the service area and I don't have to consider itù
        # create a spatial index for the drive graph layer
        drive_graph_index = QgsSpatialIndex(drive_graph_layer.getFeatures())

        # iterate over the features of the service area layer
        for service_area_feature in service_area_layer.getFeatures():
            # get the geometry of the service area feature
            service_area_geometry = service_area_feature.geometry()

            # find the features that intersect with the service area feature
            intersecting_drive_graph_ids = drive_graph_index.intersects(service_area_geometry.boundingBox())

            # iterate over the features that intersect with the service area feature
            for drive_graph_id in intersecting_drive_graph_ids:
                # get the feature
                drive_graph_feature = drive_graph_layer.getFeature(drive_graph_id)
                drive_graph_geometry = drive_graph_feature.geometry()

                # check if the service area feature intersects with the drive graph feature
                if service_area_geometry.intersects(drive_graph_geometry):
                    # get the name of the drive graph feature
                    osmid = drive_graph_feature["osmid"]
                    street_name = drive_graph_feature["name"]

                    if osmid not in intersections_dict:
                        # add to the dictionary. The key is the name of the street while the the value are the number of intersections
                        intersections_dict[(osmid, street_name)] = 1

                    # add to the dictionary. The key is the name of the street while the the value are the number of intersections
                    intersections_dict[(osmid, street_name)] += 1
        
        # write the dictionary into a json file
        with open(self._path + "/intersections.txt", "w") as outfile:
            for (id, street_name), occurrences in intersections_dict.items():
                outfile.write(f"{id} - {street_name}: {occurrences}\n")
        