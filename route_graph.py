from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsRectangle,
    QgsGeometry,
    QgsPointXY,
    QgsField,
    QgsSpatialIndex,
)

from .resources import *
import os.path

from .gtfs_db import Database
from .utils import change_style_layer

from collections import defaultdict
import networkx as nx
import osmnx as ox
import datetime

EARTH_CIRCUMFERENCE_DIVIDED_BY_360 = 111320
RADIUS = 400 / EARTH_CIRCUMFERENCE_DIVIDED_BY_360
STOP_RADIUS = 100 / EARTH_CIRCUMFERENCE_DIVIDED_BY_360


class RouteGraph:
    def create_graph_for_routes(self):
        """Create a graph that represents the route with networkx.
        shape = [shape_id, shape_pt_lat, shape_pt_lon, shape_pt_sequence]"""

        GRAPH_PATH_GPKG = self._path + "/graphs/routes_graph.gpkg"
        GRAPH_PATH_GML = self._path + "/graphs/routes_graph.graphml"
        LAYER_NAME = "routes_graph"

        project = QgsProject.instance()

        if os.path.exists(GRAPH_PATH_GPKG):
            if len(project.mapLayersByName(LAYER_NAME)) == 2:
                return
            else:
                self.load_routes_layer(GRAPH_PATH_GPKG, LAYER_NAME)
                return

        print("Creating graph for routes...")

        database = Database()
        shapes = database.select_all_coordinates_shapes()

        if not shapes:
            return "Error: routes is empty"

        shape_id = ""
        is_first_value = True

        G = nx.MultiDiGraph()
        G.graph["crs"] = "EPSG:4326"

        for shape in shapes:
            # check if is the first value
            if shape[0] != shape_id:
                is_first_value = True

            if is_first_value:
                shape_id = shape[0]
                is_first_value = False

                transport_info = database.select_transport_by_shape_id(shape_id)
                # the result is composed by one tuple and is composed by transport and route_type
                transport = str(transport_info[0][0])
                route_type = int(transport_info[0][1])

                # update previous shape
                prev_shape = shape

                G.add_node(
                    shape[0] + "_" + str(shape[3]),
                    x=float(shape[2]),
                    y=float(shape[1]),
                    is_stop=False,
                )
            else:
                G.add_node(
                    shape[0] + "_" + str(shape[3]),
                    x=float(shape[2]),
                    y=float(shape[1]),
                    is_stop=False,
                )

                # calculate euclidean distance between previous shape and current shape
                euclidean_distance = ox.distance.great_circle_vec(
                    float(prev_shape[2]), float(prev_shape[1]), float(shape[2]), float(shape[1])
                )

                starting_node = prev_shape[0] + "_" + str(prev_shape[3])
                ending_node = shape[0] + "_" + str(shape[3])
                G.add_edge(
                    starting_node,
                    ending_node,
                    weight=euclidean_distance,
                    transport=transport,
                    route_type=route_type,
                )

                # update previous shape
                prev_shape = shape

        print("Graph created!")

        self.modify_graph(G)

        # import and save it as a GeoPackage and as GraphML file
        print("Saving graph as GRAPHML and GeoPackage file...")

        if not os.path.exists(self._path + "/graphs"):
            os.makedirs(self._path + "/graphs")

        # ox.save_graphml(G, filepath=graph_path_gml)
        nx.write_graphml(G, GRAPH_PATH_GML)
        print("Graph saved as GRAPHML file!")
        ox.save_graph_geopackage(G, filepath=GRAPH_PATH_GPKG, directed=True)
        print("Graph saved as GeoPackage file!")

        # load graph as layer
        self.load_routes_layer(GRAPH_PATH_GPKG, "routes_graph")

    def load_routes_layer(self, layer_path: str, layer_name: str):
        """Load routes layer"""

        print("Loading route graph...")

        project = QgsProject.instance()
        layer_point = QgsVectorLayer(layer_path + "|layername=nodes", layer_name, "ogr")
        layer_line = QgsVectorLayer(layer_path + "|layername=edges", layer_name, "ogr")
        if not layer_point.isValid() or not layer_line.isValid():
            print("Layer failed to load!")
        else:
            print("Route graph loaded!")
            project.addMapLayer(layer_point)
            project.addMapLayer(layer_line)

        change_style_layer(layer_point, "circle", "orange", "0.5", None)
        change_style_layer(layer_line, None, "orange", None, "0.5")

    def modify_graph(self, G: nx.MultiDiGraph):
        """Modifies the graph `G` by merging nodes with the same coordinates and merging stops with the graph."""

        GRAPH_PATH_GML = self._path + "/graphs/pedestrian_graph.graphml"

        print("Modifying graph...")

        # Create a dictionary of coordinates
        coords = defaultdict(list)
        for node, data in G.nodes(data=True):
            coords[(data["x"], data["y"])].append(node)

        print("Merging nodes with same coordinates...")
        for coord, nodes in coords.items():
            if len(nodes) > 1:
                self.merge_graph_nodes_with_same_coordinates(G, nodes, coord)
        print("Nodes merged!")

        self.merge_stops_with_graph(G)

        self.get_subgraphs(G)

        G_walk = ox.load_graphml(
            GRAPH_PATH_GML,
            node_dtypes={"fid": int, "osmid": str, "x": float, "y": float},
            edge_dtypes={
                "fid": int,
                "u": str,
                "v": str,
                "key": int,
                "weight": float,
                "transport": str,
                "from": str,
                "to": str,
            },
        )
        self.merge_subgraphs(G, G_walk)

        print("Graph modified!")

        self.get_subgraphs(G)

    def merge_graph_nodes_with_same_coordinates(
        self, G: nx.MultiDiGraph, nodes: list, coord: tuple
    ):
        """Merge the selected `nodes` in the graph `G` into one `new_node`, considering edge directions."""

        # id of the new node is the concatenation of the ids of the merged nodes
        node_id = "-".join(nodes)

        G.add_node(node_id, x=coord[0], y=coord[1], is_stop=False)

        for node in nodes:
            edges_out = G.edges(node, data=True, keys=True)
            edges_in = G.in_edges(node, data=True, keys=True)

            for u, v, k, data in edges_out:
                G.add_edge(node_id, v, key=k, **data)

            for u, v, k, data in edges_in:
                G.add_edge(u, node_id, key=k, **data)
            G.remove_node(node)

    def merge_stops_with_graph(self, G: nx.MultiDiGraph):
        """Merges the stops with the graph."""
        # Possible improvements: use a spatial index to speed up the process

        print("Merging stops with the graph...")
        print(len(G.nodes()), " nodes in the routes graph")

        database = Database()
        stops = database.select_all_coordinates_stops()

        feature_id_graph_to_point = defaultdict(dict)
        point_to_id_graph = defaultdict(dict)

        # create a spatial index of the graph
        spatial_index_graph = QgsSpatialIndex()
        sub_spatial_index_graph = QgsSpatialIndex()
        for node, id in zip(G.nodes(), range(len(G.nodes()))):
            x = float(G.nodes[node]["x"])
            y = float(G.nodes[node]["y"])
            point_graph = QgsPointXY(x, y)
            point_to_id_graph[point_graph] = node

            feature_graph = QgsFeature()
            feature_graph.setGeometry(QgsGeometry.fromPointXY(point_graph))
            feature_graph.setId(id)
            spatial_index_graph.addFeature(feature_graph)
            feature_id_graph_to_point[id] = point_graph

        for stop in stops:
            stop_point = QgsPointXY(float(stop[3]), float(stop[2]))

            # define the dimensions of the bounding box
            x_min = stop_point.x() - STOP_RADIUS
            y_min = stop_point.y() - STOP_RADIUS
            x_max = stop_point.x() + STOP_RADIUS
            y_max = stop_point.y() + STOP_RADIUS

            bounding_box = QgsRectangle(x_min, y_min, x_max, y_max)

            intersecting_features = spatial_index_graph.intersects(bounding_box)

            # create a sub spatial index
            for feature in intersecting_features:
                feature_graph = QgsFeature()
                sub_point = feature_id_graph_to_point[feature]
                feature_graph.setGeometry(QgsGeometry.fromPointXY(sub_point))
                feature_graph.setId(feature)
                sub_spatial_index_graph.addFeature(feature_graph)

            nearest_node = sub_spatial_index_graph.nearestNeighbor(stop_point, 1, 0)[0]
            nearest_point = feature_id_graph_to_point[nearest_node]
            nearest_node_id = point_to_id_graph[nearest_point]

            G.nodes[nearest_node_id]["is_stop"] = True

        print("Stops merged!")

    def convert_nodes_into_points(self, G: nx.MultiDiGraph):
        """Convert nodes into points"""

        print("Converting stop nodes into points...")
        print(len(G.nodes()), " nodes in the routes graph")

        # create a default dictionary to store the nodes with the attribute id
        point_to_id_stop = defaultdict(dict)
        feature_id_stop_to_point = defaultdict(dict)

        # create a spatial index
        spatial_index_stops = QgsSpatialIndex()

        stop_points = []

        # create a list of points and fill a dictionary with the nodes with the attribute id
        for node, id in zip(G.nodes, range(len(G.nodes))):
            x = float(G.nodes[node]["x"])
            y = float(G.nodes[node]["y"])
            is_stop = G.nodes[node]["is_stop"]

            if is_stop == True:
                point = QgsPointXY(x, y)
                point_to_id_stop[point] = node
                stop_points.append(point)

                feature_stop = QgsFeature()
                feature_stop.setGeometry(QgsGeometry.fromPointXY(point))
                feature_stop.setId(id)
                spatial_index_stops.addFeature(feature_stop)
                feature_id_stop_to_point[feature_stop.id()] = point

        print("Stop nodes converted into points!")

        return (
            stop_points,
            point_to_id_stop,
            spatial_index_stops,
            feature_id_stop_to_point,
        )

    def convert_walk_nodes_into_points(self, G: nx.MultiDiGraph):
        """Convert walk nodes into points"""

        print("Converting walk nodes into points...")
        print(len(G.nodes()), " nodes in the walk graph")

        start_time = datetime.datetime.now()

        point_to_id_walk = defaultdict(dict)
        feature_id_walk_to_point = defaultdict(dict)

        # create a spatial index
        spatial_index_walk = QgsSpatialIndex()

        for node, id in zip(G.nodes, range(len(G.nodes))):
            x = float(G.nodes[node]["x"])
            y = float(G.nodes[node]["y"])
            point = QgsPointXY(x, y)
            point_to_id_walk[point] = node

            feature_walk = QgsFeature()
            feature_walk.setGeometry(QgsGeometry.fromPointXY(point))
            feature_walk.setId(id)
            spatial_index_walk.addFeature(feature_walk)
            feature_id_walk_to_point[feature_walk.id()] = point

        print("Walk nodes converted into points!")

        end_time = datetime.datetime.now()
        print("Total operation time: ", end_time - start_time)

        return point_to_id_walk, spatial_index_walk, feature_id_walk_to_point

    def merge_subgraphs(self, G: nx.MultiDiGraph, G_walk: nx.MultiDiGraph):
        """Merge subgraphs"""

        # Possible improvement: Provare a rimuovere gli archi a piedi fra i due punti collegandoli direttamente con il path reale. Per fare ció l'idea é quella di creare un
        # grafo secondario dove mettere solo le connessioni mentre in quello grande mettere lo shortest path.

        print("Merging subgraphs...")

        (
            stop_points,
            point_to_id_stop,
            spatial_index_stops,
            feature_id_stop_to_point,
        ) = self.convert_nodes_into_points(G)
        (
            point_to_id_walk,
            spatial_index_walk,
            feature_id_walk_to_point,
        ) = self.convert_walk_nodes_into_points(G_walk)

        start_time = datetime.datetime.now()
        print("Start time: ", start_time)

        for stop_point, i in zip(stop_points, range(len(stop_points))):
            # define the rectangle area for the current stop point
            x_min = stop_point.x() - RADIUS
            y_min = stop_point.y() - RADIUS
            x_max = stop_point.x() + RADIUS
            y_max = stop_point.y() + RADIUS

            rectangle_area = QgsRectangle(x_min, y_min, x_max, y_max)

            intersected_stop_features = spatial_index_stops.intersects(rectangle_area)

            if len(intersected_stop_features) > 0:
                current_walk_point_feature_id = spatial_index_walk.nearestNeighbor(
                    stop_point, 1, 0
                )[
                    0
                ]  # return a list of ID ordered by distance

                current_walk_point = feature_id_walk_to_point[
                    current_walk_point_feature_id
                ]

                current_walk_point_id = point_to_id_walk[current_walk_point]
                current_stop_point_id = point_to_id_stop[stop_point]

                for stop_feature_id in intersected_stop_features:
                    intersected_stop_point = feature_id_stop_to_point[stop_feature_id]
                    # intersected_stop_point_geometry = spatial_index_stops.geometry(stop_feature_id) prova questa alternativa e ottenere la geometria

                    intersected_stop_point_id = point_to_id_stop[intersected_stop_point]
                    # define the area of the rectangle for the intersected stop point
                    x_min = intersected_stop_point.x() - RADIUS
                    y_min = intersected_stop_point.y() - RADIUS
                    x_max = intersected_stop_point.x() + RADIUS
                    y_max = intersected_stop_point.y() + RADIUS

                    rectangle_area = QgsRectangle(x_min, y_min, x_max, y_max)

                    intersected_walk_features = spatial_index_walk.intersects(
                        rectangle_area
                    )

                    # create a sub spatial index with the intersected walk points
                    sub_spatial_index_walk = QgsSpatialIndex()

                    for intersected_walk_feature_id in intersected_walk_features:
                        sub_feature_walk = QgsFeature()
                        sub_point = feature_id_walk_to_point[
                            intersected_walk_feature_id
                        ]
                        sub_feature_walk.setGeometry(QgsGeometry.fromPointXY(sub_point))
                        sub_feature_walk.setId(intersected_walk_feature_id)
                        sub_spatial_index_walk.addFeature(sub_feature_walk)

                    if intersected_stop_point != stop_point and not G.has_edge(
                        current_stop_point_id, intersected_stop_point_id
                    ):
                        if len(intersected_walk_features) == 0:
                            nearest_walk_point_feature_id = (
                                spatial_index_walk.nearestNeighbor(
                                    intersected_stop_point, 1, 0
                                )[0]
                            )
                        else:
                            nearest_walk_point_feature_id = (
                                sub_spatial_index_walk.nearestNeighbor(
                                    intersected_stop_point, 1, 0
                                )[0]
                            )  # return a list of ID ordered by distance

                        nearest_walk_point = feature_id_walk_to_point[
                            nearest_walk_point_feature_id
                        ]

                        nearest_walk_point_id = point_to_id_walk[nearest_walk_point]

                        distance_meters = nx.shortest_path_length(
                            G_walk,
                            current_walk_point_id,
                            nearest_walk_point_id,
                            weight="length",
                        )

                        G.add_edge(
                            current_stop_point_id,
                            intersected_stop_point_id,
                            weight=distance_meters,
                            transport="walk",
                            route_type=15,
                        )
            else:
                print("No points found!")

            if i % 50 == 0:
                partial_time = datetime.datetime.now()
                print("Point ", i, " of ", len(stop_points), " processed")
                print("Partial time: ", partial_time - start_time)
        
        end_time = datetime.datetime.now()
        print("Total operation time: ", end_time - start_time)
        print("Subgraphs merged!")

    def get_subgraphs(self, G: nx.MultiDiGraph):
        """Get subgraphs of a MultiDiGraph"""

        print("Extracting subgraphs...")

        connected_components = list(nx.weakly_connected_components(G))
        print("Number of subgraphs: ", len(connected_components))

        project = QgsProject.instance()

        # create a layer for each subgraph
        for i, component in enumerate(connected_components):
            subG = G.subgraph(component)
            name = "subgraph_" + str(i + 1)
            layer = QgsVectorLayer("LineString?crs=epsg:4326", name, "memory")
            layer.dataProvider().addAttributes([QgsField("Component", QVariant.Int)])
            layer.updateFields()

            # add the subgraph to the layer
            for edge in subG.edges:
                node1 = subG.nodes[edge[0]]
                node2 = subG.nodes[edge[1]]

                point1 = QgsPointXY(float(node1["x"]), float(node1["y"]))
                point2 = QgsPointXY(float(node2["x"]), float(node2["y"]))

                feature = QgsFeature()
                feature.setGeometry(QgsGeometry.fromPolylineXY([point1, point2]))
                feature.setAttributes([i])
                layer.dataProvider().addFeatures([feature])

            change_style_layer(layer, None, "yellow", None, "0.5")

            project.addMapLayer(layer)
            print("Subgraph ", i + 1, " loaded")

        print("Subgraphs extracted!")
