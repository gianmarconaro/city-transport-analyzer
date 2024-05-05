from qgis.PyQt.QtCore import Qt
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
from qgis.core import QgsProject
from qgis.utils import iface
from qgis.core import Qgis

from .resources import *

from .gtfs_db import Database
from .service_area_analysis import *
from .nearby_stops_paths_analysis import *

import networkx as nx


def get_inputs_from_dialog_multi_analysis(inputs):
    """Get the inputs from the dialog and return them."""

    dialog = QDialog()
    dialog.setWindowTitle("Multi Analysis")

    layout = QVBoxLayout()
    dialog.setFixedSize(400, 325)

    label = QLabel("Select the points layer to analyse the service area:")
    layout.addWidget(label)

    # create the combo box for service area analysis
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

    label = QLabel("Insert the time of the service area analysis:")
    layout.addWidget(label)

    # create a line edit
    inputs.time_line_edit = QLineEdit()
    inputs.time_line_edit.setPlaceholderText("Time (m) [5-20]")
    inputs.time_line_edit.setValidator(QIntValidator(5, 20))
    layout.addWidget(inputs.time_line_edit)

    # create a checkbox
    inputs.checkbox = QCheckBox(
        "Detailed Analysis (May affect drastically the performance)"
    )
    layout.addWidget(inputs.checkbox)

    label = QLabel("Select the points layer to analyse the nearby stops:")
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

    inputs.stops_combo_box = QComboBox()
    inputs.stops_combo_box.addItems(active_vector_layers_names)
    inputs.stops_combo_box.setPlaceholderText("Points Layer")
    inputs.stops_combo_box.setEditable(True)
    inputs.stops_combo_box.setMaxVisibleItems(5)

    # define compleater
    compleater = QCompleter(active_vector_layers_names)
    compleater.setCaseSensitivity(Qt.CaseInsensitive)

    inputs.stops_combo_box.setCompleter(compleater)
    layout.addWidget(inputs.stops_combo_box)

    label = QLabel("Insert the range of the nearby stops analysis:")
    layout.addWidget(label)

    # create a line edit
    inputs.range_line_edit = QLineEdit()
    inputs.range_line_edit.setPlaceholderText("Range (m) [100-2000]")
    inputs.range_line_edit.setValidator(QIntValidator(100, 2000))
    layout.addWidget(inputs.range_line_edit)

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
        inputs.stops_combo_box.currentText()
    )

    points = []
    layer_name = inputs.points_combo_box.currentText()
    points_layer = QgsProject.instance().mapLayersByName(layer_name)[0]
    for feature in points_layer.getFeatures():
        points.append(feature.geometry().asPoint())
    time = inputs.time_line_edit.text()

    stop_points = []
    layer_name = inputs.points_combo_box.currentText()
    points_layer = QgsProject.instance().mapLayersByName(layer_name)[0]
    for feature in points_layer.getFeatures():
        stop_points.append(feature.geometry().asPoint())
    range = inputs.range_line_edit.text()

    precise_analysis = inputs.checkbox.isChecked()

    # managing errors
    handle_multi_analysis_inputs_errors(range, time)

    return points, stop_points, int(range), int(time), precise_analysis


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
    if starting_dialog:
        starting_dialog.close()

    try:
        (
            points,
            stop_points,
            range,
            time,
            checkbox,
        ) = get_inputs_from_dialog_multi_analysis(inputs)
    except TypeError:
        return

    crs = QgsProject.instance().crs()

    number_analysis = get_number_analysis()

    # service area analysis
    service_area_analysis_operations(crs, points, time, checkbox, G, G_walk, number_analysis)

    # nearby stops analysis
    nearby_stops_paths_analysis_operations(inputs, crs, stop_points, range, G_walk, number_analysis)
