from qgis.core import QgsProject
from qgis.utils import iface

from .resources import *

import os
import shutil


def get_number_analysis():
    """Calculate the number of the analysis to do"""
    project = QgsProject.instance()

    layers_to_check = [
        "service_area_",
        "shortest_paths_",
        "starting_points_",
        "starting_stops_",
        "selected_stops_",
        "circular_buffer_",
        "convex_polygons_",
    ]

    layers_number = []

    # for each layer, check if exists and if exists, get the higher number of the layer
    for layer_to_check in layers_to_check:
        layers = project.mapLayers().values()
        layers = [layer for layer in layers if layer.name().startswith(layer_to_check)]
        for layer in layers:
            layer_name = layer.name()
            layer_number = layer_name.split("_")[-1]
            if layer_number.isnumeric():
                layers_number.append(int(layer_number))

    if layers_number:
        return max(layers_number) + 1
    else:
        return 1


def remove_all_project_layers():
    """Delete all data from graph folder, shapefiles folder, polygons folder and database"""
    project = QgsProject.instance()

    layers_to_remove = [
        "circular_buffer_",
        "selected_stops_",
        "shortest_paths_",
        "starting_points_",
        "starting_stops_",
        "service_area_",
        "convex_polygons_",
        "intersections_",
    ]

    remove_stops_layer()
    remove_graphs_layers()

    for layer in project.instance().mapLayers().values():
        for layer_to_remove in layers_to_remove:
            if layer.name().startswith(layer_to_remove):
                last_char = layer.name()[-1]
                if last_char.isnumeric():
                    project.removeMapLayer(layer)

    canvas = iface.mapCanvas()
    canvas.refresh()


def delete_all_project_folders():
    """Delete all data from graph folder, shapefiles folder, polygons folder and database"""

    folders_to_remove = ["graphs", "shapefiles", "polygons", "GTFS_DB"]

    for folder in folders_to_remove:
        folder_path = os.path.join(os.path.dirname(__file__), folder)
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)


def remove_stops_layer():
    """Remove stops layer from the project"""

    project = QgsProject.instance()

    # layer names pattern
    LAYER_PATTERN = [
        "stops",
    ]

    # check if the layer is already present. If is present, delete it
    project = QgsProject.instance()
    for layer_pattern in LAYER_PATTERN:
        layers = project.mapLayersByName(layer_pattern)
        for layer in layers:
            project.removeMapLayer(layer)

    canvas = iface.mapCanvas()
    canvas.refresh()


def delete_shapefiles_folder():
    """Delete shapefiles folder"""

    folder_path = os.path.join(os.path.dirname(__file__), "shapefiles")
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)


def remove_graphs_layers():
    """Remove graphs layers from the project"""

    project = QgsProject.instance()

    # layer names pattern
    LAYER_PATTERN = [
        "routes_graph",
    ]

    # check if the layer is already present. If is present, delete it
    project = QgsProject.instance()
    for layer_pattern in LAYER_PATTERN:
        layers = project.mapLayersByName(layer_pattern)
        for layer in layers:
            project.removeMapLayer(layer)


def remove_polygon_graphs_layers():
    """Remove graphs layers from the project"""

    project = QgsProject.instance()

    # layer names pattern
    LAYER_PATTERN = [
        "pedestrian_graph",
    ]

    # check if the layer is already present. If is present, delete it
    project = QgsProject.instance()
    for layer_pattern in LAYER_PATTERN:
        layers = project.mapLayersByName(layer_pattern)
        for layer in layers:
            project.removeMapLayer(layer)

    # i wanna to remove also the file from project folder
    # remove_cached_graphs("pedestrian_graph.graphml.xml")


def remove_cached_graphs():
    """Remove graph cache files"""
    # remove 4 files from graphs folder
    cache_folder = os.path.join(os.path.dirname(__file__), "graphs")

    cache_file_names = [
        "pedestrian_graph.gpkg",
        "pedestrian_graph.graphml.xml",
    ]

    for cache_file_name in cache_file_names:
        cache_file_path = os.path.join(cache_folder, cache_file_name)

        # check if the file exists. If exists, close it and delete it
        if os.path.exists(cache_file_path):
            # delete the file
            os.remove(cache_file_path)
