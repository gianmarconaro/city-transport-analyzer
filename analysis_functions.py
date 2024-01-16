from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QProgressDialog

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsFields,
    QgsField,
    QgsFillSymbol,
    QgsDistanceArea,
    QgsUnitTypes,
    QgsSpatialIndex,
    QgsCoordinateReferenceSystem,
)

from .resources import *

from .gtfs_db import Database
from .utils import change_style_layer, route_type_to_speed

from collections import defaultdict, deque
import networkx as nx
import osmnx as ox


def create_and_load_nearest_starting_point(
    G: nx.DiGraph,
    crs: QgsCoordinateReferenceSystem,
    fields: QgsFields,
    starting_point_geometry: QgsGeometry,
):
    """Create a layer to store the nearest starting point and fill it with the nearest starting point"""

    # calculate the nearest node of the starting point
    nearest_node = ox.nearest_nodes(
        G,
        starting_point_geometry.asPoint().x(),
        starting_point_geometry.asPoint().y(),
    )

    nearest_node_x = G.nodes[nearest_node]["x"]
    nearest_node_y = G.nodes[nearest_node]["y"]

    nearest_node_point = QgsPointXY(nearest_node_x, nearest_node_y)

    nearest_starting_point_layer = QgsVectorLayer(
        "Point?crs=" + crs.authid(), "starting_point_route", "memory"
    )

    nearest_starting_point_layer.dataProvider().addAttributes(fields)
    nearest_starting_point_layer.startEditing()

    # create a new feature
    new_feature = QgsFeature(nearest_starting_point_layer.fields())
    new_feature.setGeometry(QgsGeometry.fromPointXY(nearest_node_point))
    nearest_starting_point_layer.addFeature(new_feature)

    nearest_starting_point_layer.commitChanges()

    change_style_layer(nearest_starting_point_layer, "square", "blue", "2", None)

    project = QgsProject.instance()
    project.addMapLayer(nearest_starting_point_layer)

    return nearest_node


def create_and_load_layer_circular_buffer(
    crs: QgsCoordinateReferenceSystem,
    nearest_stops: list,
    stops_layer: QgsVectorLayer,
    range: int,
    number_analysis: int,
):
    """Create a layer to store the circular buffer and fill it with the circular buffer"""

    project = QgsProject.instance()

    circular_buffer_list = []

    circular_buffer_layer = QgsVectorLayer(
        "Polygon?crs=" + crs.authid(), f"circular_buffer_{number_analysis}", "memory"
    )

    for stop in nearest_stops:
        x_coord = stop[2][0]
        y_coord = stop[2][1]

        starting_point = QgsPointXY(x_coord, y_coord)
        starting_point_geometry = QgsGeometry.fromPointXY(starting_point)

        # create distance area
        distance_area = QgsDistanceArea()
        distance_area.setSourceCrs(stops_layer.crs(), project.transformContext())
        distance_area.setEllipsoid(project.ellipsoid())

        distance_degrees = distance_area.convertLengthMeasurement(
            range, QgsUnitTypes.DistanceDegrees
        )

        # create a circular buffer
        circular_buffer = starting_point_geometry.buffer(distance_degrees, segments=32)
        circular_feature = QgsFeature()
        circular_feature.setGeometry(circular_buffer)

        circular_buffer_layer.dataProvider().addFeatures([circular_feature])

        fill_symbol = QgsFillSymbol.createSimple(
            {
                "color": "cyan",
                "outline_color": "black",
                "outline_width": "0.5",
                "style": "solid",
            }
        )
        fill_symbol.setColor(QColor(0, 255, 255, 80))
        circular_buffer_layer.renderer().setSymbol(fill_symbol)

        circular_buffer_list.append(circular_buffer)

    project.addMapLayer(circular_buffer_layer)

    return circular_buffer_list


def create_and_load_layer_selected_stops(
    crs: QgsCoordinateReferenceSystem,
    stops_layer: QgsVectorLayer,
    circular_buffer_list: list,
    transport_list: list,
    stops: list,
    number_analysis: int,
):
    """Create a layer to store the selected stops and fill it with the selected stops"""

    selected_stops_dict = defaultdict(list)
    selected = False

    project = QgsProject.instance()

    fields = QgsFields()
    fields.append(QgsField("start_ID", QVariant.String))
    fields.append(QgsField("target_ID", QVariant.String))
    fields.append(QgsField("Stop_name", QVariant.String))
    fields.append(QgsField("Selected", QVariant.Int))
    fields.append(QgsField("Transports", QVariant.String))

    selected_stops_layer = QgsVectorLayer(
        "Point?crs=" + crs.authid(), f"selected_stops_{number_analysis}", "memory"
    )

    selected_stops_layer.dataProvider().addAttributes(fields)
    selected_stops_layer.startEditing()

    # create a spatial index for the stops layer (the bigger one)
    stops_index = QgsSpatialIndex(stops_layer.getFeatures())

    for circular_buffer, starting_transport_list, stop in zip(
        circular_buffer_list, transport_list, stops
    ):
        intersecting_stop_ids = stops_index.intersects(circular_buffer.boundingBox())
        starting_stop_id = stop[0]

        print(f"Starting point transports: ", ", ".join(starting_transport_list))

        for stop_id in intersecting_stop_ids:
            feature = stops_layer.getFeature(stop_id)
            stop_point = feature.geometry()

            selected_stop_transports = Database().select_transports_by_stop_id(
                feature["ID"]
            )
            selected_stop_transports_list = [
                transport[0] for transport in selected_stop_transports
            ]
            selected_stop_transports_string = ", ".join(selected_stop_transports_list)

            if circular_buffer.contains(stop_point):
                new_feature = QgsFeature(selected_stops_layer.fields())
                new_feature.setGeometry(stop_point)
                if feature["ID"] != starting_stop_id:
                    if set(starting_transport_list).intersection(
                        set(selected_stop_transports_list)
                    ):
                        new_feature.setAttributes(
                            [
                                starting_stop_id,
                                feature["ID"],
                                feature["Stop_name"],
                                0,
                                selected_stop_transports_string,
                            ]
                        )
                    else:
                        new_feature.setAttributes(
                            [
                                starting_stop_id,
                                feature["ID"],
                                feature["Stop_name"],
                                1,
                                selected_stop_transports_string,
                            ]
                        )

                        selected = True

                        selected_stops_dict[starting_stop_id].append(
                            [feature["ID"], feature["Stop_name"], stop_point]
                        )

                    selected_stops_layer.addFeature(new_feature)

    selected_stops_layer.commitChanges()

    change_style_layer(selected_stops_layer, "square", "yellow", "2", None)

    project.addMapLayer(selected_stops_layer)

    return selected_stops_dict, selected


def create_and_load_layer_shortest_paths(
    crs: QgsCoordinateReferenceSystem,
    nearest_stops: list,
    selected_stops_dict: dict,
    G_walk: nx.Graph,
    number_analysis: int,
):
    """Create a layer to store the shortest paths and fill it with the shortest paths"""

    if not selected_stops_dict:
        print("No admitted stops found")
        return

    shortest_paths_layer = QgsVectorLayer(
        "LineString?crs=" + crs.authid(), f"shortest_paths_{number_analysis}", "memory"
    )

    fields = QgsFields()
    fields.append(QgsField("From", QVariant.String))
    fields.append(QgsField("From_Stop_Name", QVariant.String))
    fields.append(QgsField("To", QVariant.String))
    fields.append(QgsField("To_Stop_Name", QVariant.String))
    fields.append(QgsField("Length", QVariant.Double))

    shortest_paths_layer.dataProvider().addAttributes(fields)
    shortest_paths_layer.startEditing()

    for stop in nearest_stops:
        current_stop_id = stop[0]
        current_stop_name = stop[1]
        x_coord = stop[2][0]
        y_coord = stop[2][1]

        starting_point_nearest_node = ox.nearest_nodes(G_walk, x_coord, y_coord)

        if current_stop_id in selected_stops_dict:
            for selected_stop in selected_stops_dict[current_stop_id]:
                selected_stop_id = selected_stop[0]
                selected_stop_name = selected_stop[1]
                selected_stop_point = selected_stop[2].asPoint()

                stop_nearest_node = ox.nearest_nodes(
                    G_walk, selected_stop_point.x(), selected_stop_point.y()
                )

                shortest_path = nx.shortest_path(
                    G_walk,
                    starting_point_nearest_node,
                    stop_nearest_node,
                    weight="length",
                )

                shortest_paths_length = nx.shortest_path_length(
                    G_walk,
                    starting_point_nearest_node,
                    stop_nearest_node,
                    weight="length",
                )

                path_line = [
                    QgsPointXY(G_walk.nodes[node]["x"], G_walk.nodes[node]["y"])
                    for node in shortest_path
                ]

                path_geometry = QgsGeometry.fromPolylineXY(path_line)
                # create a new feature
                new_feature = QgsFeature(shortest_paths_layer.fields())
                new_feature.setGeometry(path_geometry)
                new_feature.setAttributes(
                    [
                        current_stop_id,
                        current_stop_name,
                        selected_stop_id,
                        selected_stop_name,
                        shortest_paths_length,
                    ]
                )

                shortest_paths_layer.addFeature(new_feature)

    shortest_paths_layer.commitChanges()

    change_style_layer(shortest_paths_layer, None, "orange", None, "0.5")

    project = QgsProject.instance()
    project.addMapLayer(shortest_paths_layer)
    print("Shortest paths layer loaded")


def create_and_load_layer_reachable_nodes(
    G: nx.DiGraph,
    crs: QgsCoordinateReferenceSystem,
    starting_points: list,
    time_limit: int,
    G_walk: nx.Graph,
    checkbox: bool,
    number_analysis: int,
):
    """Calculate reachable edges in a time limit"""

    reachable_edges_list = []
    # define a queue to store the nodes to visit
    for starting_point in starting_points:
        queue = deque([(starting_point, 0)])
        reachable_edges = []
        visited_edges = set()

        while queue:
            current_node, time_elapsed = queue.popleft()
            # TODO: (1,2) added to visited_edges, but (2,1) is not added. Possible optimization
            # TODO: Not discard the edge if used one time. Can exludes some important paths

            for _, end_node, edge_data in G.out_edges(current_node, data=True):
                if (current_node, end_node) not in visited_edges:
                    distance = edge_data["weight"]  # meters
                    route_type = edge_data["route_type"]  # km/h
                    transport = edge_data["transport"]

                    speed = route_type_to_speed(route_type)
                    travel_time = (distance / 1000) / speed * 60  # minutes

                    if time_elapsed + travel_time <= time_limit:
                        reachable_edges.append(
                            (current_node, end_node, distance, transport, travel_time)
                        )
                        visited_edges.add((current_node, end_node))
                        queue.append((end_node, time_elapsed + travel_time))

        reachable_edges_list.append(reachable_edges)

    selected_id = load_layer_reachable_edges(
        G, crs, reachable_edges_list, G_walk, checkbox, number_analysis
    )

    return selected_id


def load_layer_reachable_edges(
    G: nx.DiGraph,
    crs: QgsCoordinateReferenceSystem,
    reachable_edges_list: list,
    G_walk: nx.Graph,
    checkbox: bool,
    number_analysis: int,
):
    """Create a layer to store the service area and fill it with the service area"""
    # print the number of list elements
    if not reachable_edges_list:
        print("No reachable edges found")
        return

    service_area_layer = QgsVectorLayer(
        "LineString?crs=" + crs.authid(), f"service_area_{number_analysis}", "memory"
    )

    fields = QgsFields()
    fields.append(QgsField("ID", QVariant.String))
    fields.append(QgsField("From", QVariant.String))
    fields.append(QgsField("To", QVariant.String))
    fields.append(QgsField("Weight", QVariant.Double))
    fields.append(QgsField("Transport", QVariant.String))
    fields.append(QgsField("Travel_time", QVariant.Double))

    service_area_layer.dataProvider().addAttributes(fields)
    service_area_layer.startEditing()

    service_area_id = 1
    selected_id = defaultdict(list)

    for i, reachable_edges in enumerate(reachable_edges_list):
        for edge in reachable_edges:
            # if the transport is walk, calculate the shortest path between the two nodes via pedestrian graph and add the edges to the service area
            if edge[3] == "walk" and checkbox:
                starting_point_nearest_node = ox.nearest_nodes(
                    G_walk, G.nodes[edge[0]]["x"], G.nodes[edge[0]]["y"]
                )
                ending_point_nearest_node = ox.nearest_nodes(
                    G_walk, G.nodes[edge[1]]["x"], G.nodes[edge[1]]["y"]
                )

                shortest_path = nx.shortest_path(
                    G_walk,
                    starting_point_nearest_node,
                    ending_point_nearest_node,
                    weight="length",
                )

                path_line = [
                    QgsPointXY(G_walk.nodes[node]["x"], G_walk.nodes[node]["y"])
                    for node in shortest_path
                ]
                edge_geometry = QgsGeometry.fromPolylineXY(path_line)

            else:
                edge_coordinates = [
                    (G.nodes[edge[0]]["x"], G.nodes[edge[0]]["y"]),
                    (G.nodes[edge[1]]["x"], G.nodes[edge[1]]["y"]),
                ]

                p1 = QgsPointXY(edge_coordinates[0][0], edge_coordinates[0][1])
                p2 = QgsPointXY(edge_coordinates[1][0], edge_coordinates[1][1])

                edge_geometry = QgsGeometry.fromPolylineXY([p1, p2])

            # create a new feature
            new_feature = QgsFeature(service_area_layer.fields())
            new_feature.setGeometry(edge_geometry)
            new_feature.setAttributes(
                [service_area_id, edge[0], edge[1], edge[2], edge[3], edge[4]]
            )
            service_area_layer.addFeature(new_feature)

            # build a dictionary with the selected edges and the key must be referenced to the starting point
            selected_id[i].append(service_area_id)
            service_area_id += 1

    service_area_layer.commitChanges()

    change_style_layer(service_area_layer, None, "lavander", None, "0.5")

    project = QgsProject.instance()
    project.addMapLayer(service_area_layer)

    return selected_id


def create_and_load_layer_starting_points(
    crs: QgsCoordinateReferenceSystem,
    nearest_nodes: list,
    G: nx.DiGraph,
    number_analysis: int,
):
    """Create a layer to store the starting points and fill it with the starting points"""

    project = QgsProject.instance()

    fields = QgsFields()
    fields.append(QgsField("Lat", QVariant.Double))
    fields.append(QgsField("Lon", QVariant.Double))

    starting_points_layer = QgsVectorLayer(
        "Point?crs=" + crs.authid(), f"starting_points_{number_analysis}", "memory"
    )

    starting_points_layer.dataProvider().addAttributes(fields)
    starting_points_layer.startEditing()

    for point in nearest_nodes:
        x_coord = G.nodes[point]["x"]
        y_coord = G.nodes[point]["y"]

        starting_point = QgsPointXY(x_coord, y_coord)
        starting_point_geometry = QgsGeometry.fromPointXY(starting_point)

        # create a new feature
        new_feature = QgsFeature(starting_points_layer.fields())
        new_feature.setGeometry(starting_point_geometry)
        new_feature.setAttributes([x_coord, y_coord])

        starting_points_layer.addFeature(new_feature)

    starting_points_layer.commitChanges()

    change_style_layer(starting_points_layer, "square", "blue", "2", None)

    project.addMapLayer(starting_points_layer)


def create_and_load_layer_starting_stops(
    crs: QgsCoordinateReferenceSystem, nearest_stops: list, number_analysis: int
):
    """Create a layer to store the starting stops and fill it with the starting stops"""

    transports_list = []

    project = QgsProject.instance()

    fields = QgsFields()
    fields.append(QgsField("ID", QVariant.String))
    fields.append(QgsField("Stop_name", QVariant.String))
    fields.append(QgsField("Transports", QVariant.String))

    starting_stops_layer = QgsVectorLayer(
        "Point?crs=" + crs.authid(), f"starting_stops_{number_analysis}", "memory"
    )

    starting_stops_layer.dataProvider().addAttributes(fields)
    starting_stops_layer.startEditing()

    for stop in nearest_stops:
        stop_id = stop[0]
        stop_name = stop[1]
        stop_point = stop[2]

        current_stop_transports = Database().select_transports_by_stop_id(stop_id)
        current_stop_transports_list = [
            transport[0] for transport in current_stop_transports
        ]

        transports_list.append(current_stop_transports_list)
        transports_string = ", ".join(current_stop_transports_list)

        # create a new feature
        new_feature = QgsFeature(starting_stops_layer.fields())
        stop_geometry = QgsGeometry.fromPointXY(stop_point)
        new_feature.setGeometry(stop_geometry)
        new_feature.setAttributes([stop_id, stop_name, transports_string])

        starting_stops_layer.addFeature(new_feature)

    starting_stops_layer.commitChanges()

    change_style_layer(starting_stops_layer, "square", "blue", "2", None)

    project.addMapLayer(starting_stops_layer)

    return transports_list


def create_debug_layer():
    # define a list with some points, 3 is enough
    points = [
        # RIO
        # QgsPointXY(-43.195617, -22.906821),
        # QgsPointXY(-43.3246895, -22.8472869),

        # MILANO
        # QgsPointXY(9.2006962, 45.4437618),
        # QgsPointXY(9.17593961, 45.49690061),

        # MILANO 2
        # QgsPointXY(9.1423916, 45.5303945), # NOVATE
        # QgsPointXY(9.2029287, 45.4525009), # PT ROMANA

        # QgsPointXY(9.2460641, 45.5128699), # Casa Dario
    ]

    # create fields
    fields = QgsFields()
    fields.append(QgsField("Latitude", QVariant.Double))
    fields.append(QgsField("Longitude", QVariant.Double))

    # create a layer to store the points
    points_layer = QgsVectorLayer("Point?crs=EPSG:4326", "debug_points", "memory")
    points_layer.dataProvider().addAttributes(fields)
    points_layer.startEditing()

    # create a new feature
    for point in points:
        new_feature = QgsFeature(points_layer.fields())
        new_feature.setGeometry(QgsGeometry.fromPointXY(point))
        points_layer.addFeature(new_feature)

    points_layer.commitChanges()

    change_style_layer(points_layer, "square", "red", "2", None)

    project = QgsProject.instance()
    project.addMapLayer(points_layer)
