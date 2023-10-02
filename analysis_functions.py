from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor

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
import datetime


def remove_layers(project: QgsProject):
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
        project.removeMapLayer(
            project.mapLayersByName(LAYER_NAME_STARTING_POINT_ROUTE)[0]
        )
    if project.mapLayersByName(LAYER_NAME_SERVICE_AREA):
        project.removeMapLayer(project.mapLayersByName(LAYER_NAME_SERVICE_AREA)[0])


def create_and_load_layer_starting_point(
    crs: QgsCoordinateReferenceSystem,
    fields: QgsFields,
    starting_point_geometry: QgsGeometry,
):
    """Create a layer to store the starting point and fill it with the starting point"""

    starting_point_layer = QgsVectorLayer(
        "Point?crs=" + crs.authid(), "starting_point", "memory"
    )

    starting_point_layer.dataProvider().addAttributes(fields)
    starting_point_layer.startEditing()

    # create a new feature
    new_feature = QgsFeature(starting_point_layer.fields())
    new_feature.setGeometry(starting_point_geometry)
    starting_point_layer.addFeature(new_feature)

    starting_point_layer.commitChanges()

    change_style_layer(starting_point_layer, "square", "blue", "2", None)

    project = QgsProject.instance()
    project.addMapLayer(starting_point_layer)


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
    starting_point_geometry: QgsGeometry,
    stops_layer: QgsVectorLayer,
    range: int,
):
    """Create a layer to store the circular buffer and fill it with the circular buffer"""

    project = QgsProject.instance()

    # create distance area
    distance_area = QgsDistanceArea()
    distance_area.setSourceCrs(stops_layer.crs(), project.transformContext())
    distance_area.setEllipsoid(project.ellipsoid())

    distance_degrees = distance_area.convertLengthMeasurement(
        range, QgsUnitTypes.DistanceUnit.Degrees
    )

    # create a circular buffer
    circular_buffer = starting_point_geometry.buffer(distance_degrees, segments=32)
    circular_feature = QgsFeature()
    circular_feature.setGeometry(circular_buffer)

    circular_buffer_layer = QgsVectorLayer(
        "Polygon?crs=" + crs.authid(), "circular_buffer", "memory"
    )
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

    project.addMapLayer(circular_buffer_layer)

    return circular_buffer


def create_and_load_layer_selected_stops(
    crs: QgsCoordinateReferenceSystem,
    fields: QgsFields,
    stops_layer: QgsVectorLayer,
    circular_buffer: QgsGeometry,
    current_stop_transports_list: list,
    current_stop_id: QgsGeometry,
):
    """Create a layer to store the selected stops and fill it with the selected stops"""

    selected_stops_dict = defaultdict(dict)

    project = QgsProject.instance()

    fields.append(QgsField("Transports", QVariant.String))

    selected_stops_layer = QgsVectorLayer(
        "Point?crs=" + crs.authid(), "selected_stops", "memory"
    )
    discarded_stops_layer = QgsVectorLayer(
        "Point?crs=" + crs.authid(), "discarded_stops", "memory"
    )

    selected_stops_layer.dataProvider().addAttributes(fields)
    discarded_stops_layer.dataProvider().addAttributes(fields)

    selected_stops_layer.startEditing()
    discarded_stops_layer.startEditing()

    # create a spatial index for the stops layer (the bigger one)
    stops_index = QgsSpatialIndex(stops_layer.getFeatures())

    intersecting_stop_ids = stops_index.intersects(circular_buffer.boundingBox())

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
            new_feature.setAttributes(
                [feature["ID"], feature["Stop_name"], selected_stop_transports_string]
            )

            if feature["ID"] != current_stop_id:
                # check if the intersected stop has at least one transport in common with the starting stop
                if set(current_stop_transports_list).intersection(
                    set(selected_stop_transports_list)
                ):
                    discarded_stops_layer.addFeature(new_feature)
                else:
                    selected_stops_layer.addFeature(new_feature)

                    selected_stops_dict[stop_point] = [
                        feature["ID"],
                        feature["Stop_name"],
                    ]

    selected_stops_layer.commitChanges()
    discarded_stops_layer.commitChanges()

    change_style_layer(selected_stops_layer, "square", "yellow", "2", None)
    change_style_layer(discarded_stops_layer, "square", "red", "2", None)

    project.addMapLayer(selected_stops_layer)
    project.addMapLayer(discarded_stops_layer)

    print("Starting point transports: ", ", ".join(current_stop_transports_list))

    return selected_stops_dict


def create_and_load_layer_shortest_paths(
    crs: QgsCoordinateReferenceSystem,
    selected_stops_dict: list,
    starting_stop_info: list,
    G_walk: nx.Graph,
):
    """Create a layer to store the shortest paths and fill it with the shortest paths"""

    if not selected_stops_dict:
        print("No admitted stops found")
        return

    shortest_paths_layer = QgsVectorLayer(
        "LineString?crs=" + crs.authid(), "shortest_paths", "memory"
    )

    (
        starting_stop_id,
        starting_stop_name,
        starting_point_nearest_node,
    ) = starting_stop_info

    fields = QgsFields()
    fields.append(QgsField("From", QVariant.String))
    fields.append(QgsField("From_Stop_Name", QVariant.String))
    fields.append(QgsField("To", QVariant.String))
    fields.append(QgsField("To_Stop_Name", QVariant.String))
    fields.append(QgsField("Length", QVariant.Double))

    shortest_paths_layer.dataProvider().addAttributes(fields)
    shortest_paths_layer.startEditing()

    for stop_key in selected_stops_dict:
        stop = stop_key.asPoint()

        selected_stop_id = selected_stops_dict[stop_key][0]
        selected_stop_name = selected_stops_dict[stop_key][1]

        stop_nearest_node = ox.nearest_nodes(G_walk, stop.x(), stop.y())

        shortest_path = nx.shortest_path(
            G_walk, starting_point_nearest_node, stop_nearest_node, weight="length"
        )

        shortest_paths_length = nx.shortest_path_length(
            G_walk, starting_point_nearest_node, stop_nearest_node, weight="length"
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
                starting_stop_id,
                starting_stop_name,
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
    starting_point: str,
    time_limit: int,
    G_walk: nx.Graph,
    checkbox: bool,
):
    """Calculate reachable edges in a time limit"""

    start_time = datetime.datetime.now()
    print("Starting time: ", start_time)

    # define a queue to store the nodes to visit
    queue = deque([(starting_point, 0)])
    reachable_edges = []
    visited_edges = set()

    while queue:
        current_node, time_elapsed = queue.popleft()
        # TODO: (1,2) added to visited_edges, but (2,1) is not added. Possible optimization

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

    load_layer_reachable_edges(G, crs, reachable_edges, G_walk, checkbox)


def load_layer_reachable_edges(
    G: nx.DiGraph,
    crs: QgsCoordinateReferenceSystem,
    reachable_edges: list,
    G_walk: nx.Graph,
    checkbox: bool,
):
    """Create a layer to store the service area and fill it with the service area"""

    if not reachable_edges:
        print("No reachable edges found")
        return

    service_area_layer = QgsVectorLayer(
        "LineString?crs=" + crs.authid(), "service_area", "memory"
    )

    fields = QgsFields()
    fields.append(QgsField("From", QVariant.String))
    fields.append(QgsField("To", QVariant.String))
    fields.append(QgsField("Weight", QVariant.Double))
    fields.append(QgsField("Transport", QVariant.String))
    fields.append(QgsField("Travel_time", QVariant.Double))

    service_area_layer.dataProvider().addAttributes(fields)
    service_area_layer.startEditing()

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
        new_feature.setAttributes([edge[0], edge[1], edge[2], edge[3], edge[4]])
        service_area_layer.addFeature(new_feature)

    service_area_layer.commitChanges()

    change_style_layer(service_area_layer, None, "lavander", None, "0.5")

    project = QgsProject.instance()
    project.addMapLayer(service_area_layer)
