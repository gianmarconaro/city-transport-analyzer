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
)

from qgis.utils import iface
from qgis.core import Qgis

from .resources import *

from .analysis_functions import *
from .gtfs_db import Database

import networkx as nx


def get_inputs_from_dialog_service_area(inputs):
    """Service area analysis inputs"""

    dialog = QDialog()
    dialog.setWindowTitle("Service Area Analysis")

    layout = QVBoxLayout()
    dialog.setFixedSize(400, 200)

    label = QLabel("Insert the ID of the stop that you want to analyse:")
    layout.addWidget(label)

    # create the combo box
    stop_ids = Database().select_all_stops_id()
    inputs.stop_id_combo_box = QComboBox()
    inputs.stop_id_combo_box.addItems([stop_id[0] for stop_id in stop_ids])
    inputs.stop_id_combo_box.setPlaceholderText("Stop ID")
    inputs.stop_id_combo_box.setEditable(True)
    inputs.stop_id_combo_box.setMaxVisibleItems(15)
    compleater = QCompleter([stop_id[0] for stop_id in stop_ids])
    compleater.setCaseSensitivity(Qt.CaseInsensitive)
    inputs.stop_id_combo_box.setCompleter(compleater)
    layout.addWidget(inputs.stop_id_combo_box)

    label = QLabel("Insert the time of the analysis:")
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

    stop_info = Database().select_stop_coordinates_by_id(
        inputs.stop_id_combo_box.currentText()
    )

    stop_id = inputs.stop_id_combo_box.currentText()
    time = inputs.time_line_edit.text()

    # managing errors
    handle_service_area_input_errors(time)

    precise_analysis = inputs.checkbox.isChecked()

    return stop_id, int(time), precise_analysis, stop_info[0]


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

    # close the previous dialog
    if starting_dialog:
        starting_dialog.close()
    try:
        _, time, checkbox, stop_info = get_inputs_from_dialog_service_area(inputs)
        y_coord, x_coord, _ = stop_info
    except TypeError:
        return

    crs = QgsProject.instance().crs()

    starting_point = QgsPointXY(x_coord, y_coord)
    starting_point_geometry = QgsGeometry.fromPointXY(starting_point)

    fields = QgsFields()
    fields.append(QgsField("ID", QVariant.String))
    fields.append(QgsField("Stop_name", QVariant.String))

    create_and_load_layer_starting_point(crs, fields, starting_point_geometry)

    nearest_starting_point_node = create_and_load_nearest_starting_point(
        G, crs, fields, starting_point_geometry
    )

    create_and_load_layer_reachable_nodes(
        G, crs, nearest_starting_point_node, time, G_walk, checkbox
    )
