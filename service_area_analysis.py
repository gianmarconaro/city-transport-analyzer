from qgis.PyQt.QtCore import QVariant, Qt
from qgis.PyQt.QtGui import QIntValidator
from qgis.PyQt.QtWidgets import (
    QInputDialog,
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
    QgsWkbTypes,
    QgsMapLayer,
)

from qgis.utils import iface
from qgis.core import Qgis

from .resources import *
from .analysis_functions import *

import networkx as nx


def get_inputs_from_dialog_service_area(inputs):
    """Service area analysis inputs"""

    dialog = QDialog()
    dialog.setWindowTitle("Service Area Analysis")

    layout = QVBoxLayout()
    dialog.setFixedSize(400, 200)

    label = QLabel("Select the points layer to analyse the service area:")
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

    label = QLabel("Insert the time of the service area analysis:")
    layout.addWidget(label)

    # create the line edit
    inputs.time_line_edit = QLineEdit()
    inputs.time_line_edit.setPlaceholderText("Time (m) [5-20]")
    inputs.time_line_edit.setValidator(QIntValidator(5, 20))
    layout.addWidget(inputs.time_line_edit)

    # create the checkbox
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

    if not inputs.time_line_edit.hasAcceptableInput():
        iface.messageBar().pushMessage(
            "Error",
            "Time must be within the range",
            level=Qgis.Critical,
            duration=5,
        )
        return get_inputs_from_dialog_service_area()

    points = []
    layer_name = inputs.points_combo_box.currentText()
    points_layer = QgsProject.instance().mapLayersByName(layer_name)[0]
    for feature in points_layer.getFeatures():
        points.append(feature.geometry().asPoint())
    time = inputs.time_line_edit.text()

    # managing errors
    handle_service_area_input_errors(time)

    precise_analysis = inputs.checkbox.isChecked()

    return points, int(time), precise_analysis


def handle_service_area_input_errors(time):
    """Manage errors for service area analysis"""

    # check if the time is in the range
    if time == "":
        iface.messageBar().pushMessage(
            "Error",
            "Time must be within the range",
            level=Qgis.Critical,
            duration=5,
        )
        return get_inputs_from_dialog_service_area()


def start_service_area_analysis(
    inputs, starting_dialog: QInputDialog, G: nx.DiGraph, G_walk: nx.MultiDiGraph
):
    """Start the service area analysis"""
    # prendi i punti del layer e calcola il nearest node al grafo per ogni punto, poi per ogni punto calcola il service area

    # close the previous dialog
    if starting_dialog:
        starting_dialog.close()
    try:
        points, time, checkbox = get_inputs_from_dialog_service_area(inputs)
    except TypeError:
        return

    crs = QgsProject.instance().crs()

    service_area_analysis_operations(crs, points, time, checkbox, G, G_walk)


def service_area_analysis_operations(
    crs: QgsCoordinateReferenceSystem,
    points: list,
    time: int,
    checkbox: bool,
    G: nx.DiGraph,
    G_walk: nx.MultiDiGraph,
):
    """Operations for service area analysis"""
    nearest_nodes = []
    for point in points:
        current_nearest_node = ox.nearest_nodes(G, point[0], point[1])
        nearest_nodes.append(current_nearest_node)

    for i, point in enumerate(nearest_nodes, 1):
        x_coord = G.nodes[point]["x"]
        y_coord = G.nodes[point]["y"]

        starting_point = QgsPointXY(x_coord, y_coord)
        starting_point_geometry = QgsGeometry.fromPointXY(starting_point)

        fields = QgsFields()
        fields.append(QgsField("Lat", QVariant.Double))
        fields.append(QgsField("Lon", QVariant.Double))

        create_and_load_layer_starting_point(crs, fields, starting_point_geometry, i)

        create_and_load_layer_reachable_nodes(G, crs, point, time, G_walk, checkbox, i)
