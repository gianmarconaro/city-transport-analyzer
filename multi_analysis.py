from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtGui import QIntValidator
from qgis.PyQt.QtWidgets import (
    QLineEdit,
    QDialog,
    QVBoxLayout,
    QLabel,
    QCheckBox,
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
)
from qgis.utils import iface
from qgis.core import Qgis

from .resources import *

from .gtfs_db import Database
from .service_area_analysis import *
from .nearby_stops_paths_analysis import *
from .service_area_analysis import *

import networkx as nx
import osmnx as ox


def get_inputs_from_dialog_multi_analysis(inputs):
    """Get the inputs from the dialog and return them."""

    dialog = QDialog()
    dialog.setWindowTitle("Multi Analysis")

    layout = QVBoxLayout()
    dialog.setFixedSize(400, 250)

    label = QLabel("Insert the ID of the stop that you want to analyse")
    layout.addWidget(label)

    # create the combo box
    stop_ids = Database().select_all_stops_id()
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

    # create a line edit
    inputs.range_line_edit = QLineEdit()
    inputs.range_line_edit.setPlaceholderText("Range (m) [100-2000]")
    inputs.range_line_edit.setValidator(QIntValidator(100, 2000))
    layout.addWidget(inputs.range_line_edit)

    label = QLabel("Insert the time of the analysis")
    layout.addWidget(label)

    # create a line edit
    inputs.time_line_edit = QLineEdit()
    inputs.time_line_edit.setPlaceholderText("Time (m) [5-20]")
    inputs.time_line_edit.setValidator(QIntValidator(5, 20))
    layout.addWidget(inputs.time_line_edit)

    # create a checkbox
    inputs.checkbox = QCheckBox(
        "Detailed Analysis (May affect the performance of the application)"
    )
    layout.addWidget(inputs.checkbox)

    # create a button box
    button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)

    dialog.setLayout(layout)

    result = dialog.exec_()

    if result != QDialog.Accepted:
        return

    if (
        not inputs.range_line_edit.hasAcceptableInput()
        or not inputs.time_line_edit.hasAcceptableInput()
    ):
        iface.messageBar().pushMessage(
            "Error",
            "Range and time must be within the range",
            level=Qgis.Critical,
            duration=5,
        )
        return get_inputs_from_dialog_multi_analysis()

    stop_info = Database().select_stop_coordinates_by_id(
        inputs.stop_id_combo_box.currentText()
    )

    stop_id = inputs.stop_id_combo_box.currentText()
    time = inputs.time_line_edit.text()
    range = inputs.range_line_edit.text()

    precise_analysis = inputs.checkbox.isChecked()

    # managing errors
    handle_multi_analysis_inputs_errors(range, time)

    return stop_id, int(range), int(time), precise_analysis, stop_info[0]


def handle_multi_analysis_inputs_errors(range, time):
    """Manage errors for multi analysis"""
    if time == "":
        iface.messageBar().pushMessage(
            "Error",
            "Time must be within the range",
            level=Qgis.Critical,
            duration=5,
        )
        return get_inputs_from_dialog_multi_analysis()

    if range == "":
        iface.messageBar().pushMessage(
            "Error",
            "Range and time must be within the range",
            level=Qgis.Critical,
            duration=5,
        )
        return get_inputs_from_dialog_multi_analysis()


def start_multi_analysis(
    inputs, starting_dialog: QDialog, G: nx.DiGraph, G_walk: nx.MultiDiGraph
):
    """Start the multi analysis"""
    starting_dialog.close()

    stops_layer = QgsProject.instance().mapLayersByName("stops")[0]

    try:
        (
            stop_id,
            range,
            time,
            checkbox,
            stop_info,
        ) = get_inputs_from_dialog_multi_analysis(inputs)
        y_coord, x_coord, stop_name = stop_info
    except TypeError:
        return

    crs = QgsProject.instance().crs()

    starting_point = QgsPointXY(x_coord, y_coord)
    starting_point_geometry = QgsGeometry.fromPointXY(starting_point)

    fields = QgsFields()
    fields.append(QgsField("ID", QVariant.String))
    fields.append(QgsField("Stop_name", QVariant.String))

    create_and_load_layer_starting_point(crs, fields, starting_point_geometry)

    # service area analysis
    nearest_starting_point_node = create_and_load_nearest_starting_point(
        G, crs, fields, starting_point_geometry
    )

    create_and_load_layer_reachable_nodes(
        G, crs, nearest_starting_point_node, time, G_walk, checkbox
    )

    # nearby stops analysis
    current_stop_transports = Database().select_transports_by_stop_id(stop_id)
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
        stop_id,
    )

    starting_point_nearest_node = ox.nearest_nodes(G_walk, x_coord, y_coord)

    starting_stop_info = [
        stop_id,
        stop_name,
        starting_point_nearest_node,
    ]

    if selected_stops:
        create_and_load_layer_shortest_paths(
            crs, selected_stops, starting_stop_info, G_walk
        )

        find_intersections(inputs)
