from qgis.PyQt.QtCore import Qt, QVariant
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
)
from qgis.core import (
    QgsProject,
    QgsGeometry,
    QgsPointXY,
    QgsFields,
    QgsField,
    QgsSpatialIndex,
)
from qgis.utils import iface
from qgis.core import Qgis

from .resources import *

from .analysis_functions import *
from .gtfs_db import Database

from collections import defaultdict
import networkx as nx
import osmnx as ox


def get_inputs_from_dialog_nearby_stops_paths(inputs):
    """Nearby stops analysis inputs"""

    dialog = QDialog()
    dialog.setWindowTitle("Nearby Stops Paths Analysis")

    layout = QVBoxLayout()
    dialog.setFixedSize(400, 175)

    label = QLabel("Insert the ID of the stop that you want to analyse")
    layout.addWidget(label)

    # create the combo box
    stop_ids = Database().select_all_stops_id()
    stop_ids.sort(key=lambda x: x[0])
    inputs.stop_id_combo_box = QComboBox()
    inputs.stop_id_combo_box.addItems([stop_id[0] for stop_id in stop_ids])
    inputs.stop_id_combo_box.setPlaceholderText("Stop ID")
    inputs.stop_id_combo_box.setEditable(True)
    inputs.stop_id_combo_box.setMaxVisibleItems(10)
    compleater = QCompleter([stop_id[0] for stop_id in stop_ids])
    compleater.setCaseSensitivity(Qt.CaseInsensitive)
    inputs.stop_id_combo_box.setCompleter(compleater)
    layout.addWidget(inputs.stop_id_combo_box)

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

    stop_info = Database().select_stop_coordinates_by_id(
        inputs.stop_id_combo_box.currentText()
    )

    stop_id = inputs.stop_id_combo_box.currentText()
    range = inputs.range_line_edit.text()

    # managing errors
    handle_service_area_input_errors(range)

    return stop_id, int(range), stop_info[0]


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
        current_stop_id, range, stop_info = get_inputs_from_dialog_nearby_stops_paths(
            inputs
        )
    except TypeError:
        return

    crs = QgsProject.instance().crs()

    nearby_stops_paths_analysis_operations(
        inputs, crs, current_stop_id, range, stop_info, G_walk
    )


def find_intersections(inputs):
    """Find the intersections between the drive graph and the shortest paths"""

    LAYER_NAME_DRIVE_GRAPH = "drive_graph"
    LAYER_NAME_SHORTEST_PATH = "shortest_paths"

    project = QgsProject.instance()
    drive_graph_layer = project.mapLayersByName(LAYER_NAME_DRIVE_GRAPH)[0]
    service_area_layer = project.mapLayersByName(LAYER_NAME_SHORTEST_PATH)[0]

    intersections_dict = defaultdict(list)

    # create a spatial index for the drive graph layer (the bigger one)
    drive_graph_index = QgsSpatialIndex(drive_graph_layer.getFeatures())

    for service_area_feature in service_area_layer.getFeatures():
        service_area_geometry = service_area_feature.geometry()
        intersecting_drive_graph_ids = drive_graph_index.intersects(
            service_area_geometry.boundingBox()
        )

        for drive_graph_id in intersecting_drive_graph_ids:
            drive_graph_feature = drive_graph_layer.getFeature(drive_graph_id)
            drive_graph_geometry = drive_graph_feature.geometry()

            if service_area_geometry.intersects(drive_graph_geometry):
                osmid = drive_graph_feature["osmid"]
                street_name = drive_graph_feature["name"]

                if osmid not in intersections_dict:
                    intersections_dict[(osmid, street_name)] = 1

                intersections_dict[(osmid, street_name)] += 1

    # write the result into a txt file
    with open(inputs._path + "/intersections.txt", "w") as outfile:
        for (id, street_name), occurrences in intersections_dict.items():
            outfile.write(f"{id} - {street_name}: {occurrences}\n")


def nearby_stops_paths_analysis_operations(
    inputs,
    crs: QgsCoordinateReferenceSystem,
    current_stop_id: str,
    range: int,
    stop_info,
    G_walk: nx.MultiDiGraph,
):
    """Operations for nearby stops analysis"""

    stops_layer = QgsProject.instance().mapLayersByName("stops")[0]

    str_y_coord, str_x_coord, current_stop_name = stop_info
    x_coord = float(str_x_coord)
    y_coord = float(str_y_coord)

    starting_point = QgsPointXY(x_coord, y_coord)
    starting_point_geometry = QgsGeometry.fromPointXY(starting_point)

    fields = QgsFields()
    fields.append(QgsField("ID", QVariant.String))
    fields.append(QgsField("Stop_name", QVariant.String))

    create_and_load_layer_starting_point(crs, fields, starting_point_geometry, None)

    current_stop_transports = Database().select_transports_by_stop_id(current_stop_id)
    current_stop_transports_list = [
        transport[0] for transport in current_stop_transports
    ]

    circular_buffer = create_and_load_layer_circular_buffer(
        crs, starting_point_geometry, stops_layer, range
    )

    selected_stops = create_and_load_layer_selected_stops(
        crs,
        fields,
        stops_layer,
        circular_buffer,
        current_stop_transports_list,
        current_stop_id,
    )

    starting_point_nearest_node = ox.nearest_nodes(G_walk, x_coord, y_coord)

    starting_stop_info = [
        current_stop_id,
        current_stop_name,
        starting_point_nearest_node,
    ]

    if selected_stops:
        create_and_load_layer_shortest_paths(
            crs, selected_stops, starting_stop_info, G_walk
        )

        find_intersections(inputs)
