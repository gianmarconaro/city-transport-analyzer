from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIntValidator
from qgis.PyQt.QtWidgets import (
    QInputDialog,
    QLineEdit,
    QDialog,
    QVBoxLayout,
    QLabel,
    QDialogButtonBox,
    QComboBox,
    QCompleter,
    QApplication,
    QProgressDialog,
)
from qgis.core import (
    QgsProject,
    QgsWkbTypes,
    QgsMapLayer,
    QgsSpatialIndex,
    Qgis,
    QgsCoordinateReferenceSystem,
)

from qgis.utils import iface

from .resources import *

from .analysis_functions import *
from .data_manager import get_number_analysis

import networkx as nx


def get_inputs_from_dialog_nearby_stops_paths(inputs):
    """Nearby stops analysis inputs"""

    dialog = QDialog()
    dialog.setWindowTitle("Nearby Stops Paths Analysis")

    layout = QVBoxLayout()
    dialog.setFixedSize(400, 175)

    label = QLabel("Insert the stop layer you want to analyse")
    layout.addWidget(label)

    # create combo box
    layers = QgsProject.instance().mapLayers()
    vector_layers = []
    active_vector_layers_names = []

    for layer in layers.values():
        if layer.type() == QgsMapLayer.VectorLayer:
            vector_layers.append(layer)

    for layer in vector_layers:
        if layer.geometryType() == QgsWkbTypes.PointGeometry:
            active_vector_layers_names.append(layer.name())

    inputs.points_combo_box = QComboBox()
    inputs.points_combo_box.addItems(active_vector_layers_names)
    inputs.points_combo_box.setPlaceholderText("Points Layer")
    inputs.points_combo_box.setEditable(True)
    inputs.points_combo_box.setMaxVisibleItems(5)

    # define compleater
    compleater = QCompleter(active_vector_layers_names)
    compleater.setCaseSensitivity(Qt.CaseInsensitive)

    inputs.points_combo_box.setCompleter(compleater)
    layout.addWidget(inputs.points_combo_box)

    label = QLabel("Insert the range of the analysis")
    layout.addWidget(label)

    # create the line edit
    inputs.range_line_edit = QLineEdit()
    inputs.range_line_edit.setPlaceholderText("Range (m) [100-2000]")
    inputs.range_line_edit.setValidator(QIntValidator(100, 2000))
    layout.addWidget(inputs.range_line_edit)

    dialog.setLayout(layout)

    # create the button box
    button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)

    result = dialog.exec_()

    if result != QDialog.Accepted:
        return

    if not inputs.range_line_edit.hasAcceptableInput():
        iface.messageBar().pushMessage(
            "Error",
            "Range must be within the range",
            level=Qgis.Critical,
            duration=5,
        )
        return get_inputs_from_dialog_nearby_stops_paths()

    points = []
    layer_name = inputs.points_combo_box.currentText()
    points_layer = QgsProject.instance().mapLayersByName(layer_name)[0]
    for feature in points_layer.getFeatures():
        points.append(feature.geometry().asPoint())
    range = inputs.range_line_edit.text()

    # managing errors
    handle_service_area_input_errors(range)

    return points, int(range)


def handle_service_area_input_errors(range):
    """Manage errors for nearby stops"""

    # check if the range is within the range
    if range == "":
        iface.messageBar().pushMessage(
            "Error",
            "Range and time must be within the range",
            level=Qgis.Critical,
            duration=5,
        )
        return get_inputs_from_dialog_nearby_stops_paths()


def start_nearby_stops_paths_analysis(
    inputs, starting_dialog: QInputDialog, _, G_walk: nx.MultiDiGraph
):
    """Start the nearby stops analysis"""
    if starting_dialog:
        starting_dialog.close()

    try:
        points, range = get_inputs_from_dialog_nearby_stops_paths(inputs)
    except TypeError:
        return

    crs = QgsProject.instance().crs()

    number_analysis = get_number_analysis()

    nearby_stops_paths_analysis_operations(
        inputs, crs, points, range, G_walk, number_analysis
    )


def find_intersections(inputs, number_analysis: int):
    """Find the intersections between the pedestrian graph and the shortest paths"""

    LAYER_NAME_PEDESTRIAN_GRAPH = "pedestrian_graph"
    LAYER_NAME_SHORTEST_PATH = f"shortest_paths_{number_analysis}"

    project = QgsProject.instance()
    pedestrian_graph_layer = project.mapLayersByName(LAYER_NAME_PEDESTRIAN_GRAPH)[0]
    shortest_path_layer = project.mapLayersByName(LAYER_NAME_SHORTEST_PATH)[0]

    fields = QgsFields()
    fields.append(QgsField("osmid", QVariant.String))
    fields.append(QgsField("name", QVariant.String))
    fields.append(QgsField("intersection_count", QVariant.Int))

    intersections_layer = QgsVectorLayer(
        "LineString?crs=epsg:4326", f"intersections_{number_analysis}", "memory"
    )
    intersections_layer.dataProvider().addAttributes(fields)
    intersections_layer.updateFields()

    # create a spatial index for the pedestrian graph layer (the bigger one)
    pedestrian_graph_index = QgsSpatialIndex(pedestrian_graph_layer.getFeatures())

    for shortest_path_feature in shortest_path_layer.getFeatures():
        shortest_path_geometry = shortest_path_feature.geometry()
        intersecting_pedestrian_graph_ids = pedestrian_graph_index.intersects(
            shortest_path_geometry.boundingBox()
        )

        for pedestrian_graph_id in intersecting_pedestrian_graph_ids:
            pedestrian_graph_feature = pedestrian_graph_layer.getFeature(pedestrian_graph_id)
            pedestrian_graph_geometry = pedestrian_graph_feature.geometry()

            if shortest_path_geometry.touches(pedestrian_graph_geometry) \
            or shortest_path_geometry.intersects(pedestrian_graph_geometry) \
            or shortest_path_geometry.crosses(pedestrian_graph_geometry) \
            or shortest_path_geometry.overlaps(pedestrian_graph_geometry) \
            or shortest_path_geometry.contains(pedestrian_graph_geometry) \
            or shortest_path_geometry.within(pedestrian_graph_geometry):
                osmid = pedestrian_graph_feature["osmid"]
                street_name = pedestrian_graph_feature["name"]

                found_intersection = None
                for intersection in intersections_layer.getFeatures():
                    if intersection["osmid"] == osmid:
                        found_intersection = intersection
                        break

                if found_intersection is not None:
                    intersections_layer.startEditing()
                    intersections_layer.changeAttributeValue(
                        found_intersection.id(),
                        2,
                        found_intersection["intersection_count"] + 1,
                    )
                    intersections_layer.commitChanges()
                else:
                    feature = QgsFeature(fields)
                    feature.setGeometry(pedestrian_graph_geometry)
                    feature.setAttributes([osmid, street_name, 1])
                    intersections_layer.dataProvider().addFeatures([feature])

    intersections_layer.updateExtents()
    project.addMapLayer(intersections_layer)


def nearby_stops_paths_analysis_operations(
    inputs,
    crs: QgsCoordinateReferenceSystem,
    points: list,
    range: int,
    G_walk: nx.MultiDiGraph,
    number_analysis: int,
):
    """Operations for nearby stops analysis"""
    progress_bar = QProgressDialog()
    progress_bar.setWindowTitle("Nearby Stops Paths Analysis")
    progress_bar.setLabelText("Analysis in progress...")
    progress_bar.setCancelButtonText(None)
    progress_bar.setMinimum(0)
    progress_bar.setMaximum(100)
    progress_bar.setWindowModality(2)
    progress_bar.setValue(0)

    # create a spatial index for the stops layer (the bigger one)
    stops_layer = QgsProject.instance().mapLayersByName("stops")[0]
    stops_index = QgsSpatialIndex(stops_layer.getFeatures())

    progress_bar.show()
    QApplication.processEvents()

    nearest_stop_ids = []
    for point in points:
        nearest_stop = stops_index.nearestNeighbor(point, 1)[0]
        stop_feature = stops_layer.getFeature(nearest_stop)
        current_stop_id = stop_feature["ID"]
        current_stop_name = stop_feature["Stop_name"]
        current_stop_point = stop_feature.geometry().asPoint()
        nearest_stop_ids.append(
            [current_stop_id, current_stop_name, current_stop_point]
        )

    transport_list = create_and_load_layer_starting_stops(
        crs, nearest_stop_ids, number_analysis
    )

    progress_bar.setValue(20)

    circular_buffer_list = calculate_circular_buffers(
        nearest_stop_ids, stops_layer, range
    )

    progress_bar.setValue(40)

    (
        nearest_stops_information,
        selected_stops_dict,
        selected,
    ) = create_and_load_layer_selected_stops(
        crs,
        stops_layer,
        circular_buffer_list,
        transport_list,
        nearest_stop_ids,
        number_analysis,
    )

    create_and_load_layer_circular_buffer(
        crs, nearest_stops_information, number_analysis
    )

    progress_bar.setValue(60)

    if selected:
        create_and_load_layer_shortest_paths(
            crs, nearest_stop_ids, selected_stops_dict, G_walk, number_analysis
        )

        progress_bar.setValue(80)

        find_intersections(inputs, number_analysis)

    progress_bar.setValue(100)
