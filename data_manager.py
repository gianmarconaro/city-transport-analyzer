from qgis.core import QgsProject

from .resources import *

import os
import shutil


def remove_all_project_layers():
    """Delete all data from graph folder, shapefiles folder, polygons folder and database"""
    project = QgsProject.instance()

    layers_to_remove = [
        "stops",
        "routes_graph",
        "pedestrian_graph",
        "drive_graph",
        "circular_buffer",
        "selected_stops",
        "shortest_paths",
        "starting_points",
        "starting_stops",
        "service_area",
        "convex_polygons",
    ]

    for layer in layers_to_remove:
        layers = project.mapLayersByName(layer)
        for layer in layers:
            project.removeMapLayer(layer)


def delete_all_project_folders():
    """Delete all data from graph folder, shapefiles folder, polygons folder and database"""

    folders_to_remove = ["graphs", "shapefiles", "polygons", "intersections", "GTFS_DB"]

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
        "pedestrian_graph",
        "drive_graph",
    ]

    # check if the layer is already present. If is present, delete it
    project = QgsProject.instance()
    for layer_pattern in LAYER_PATTERN:
        layers = project.mapLayersByName(layer_pattern)
        for layer in layers:
            project.removeMapLayer(layer)
