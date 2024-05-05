from qgis.PyQt.QtCore import Qt
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
    QApplication,
    QProgressDialog,
)
from qgis.core import (
    QgsProject,
    QgsWkbTypes,
    QgsMapLayer,
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsVectorLayer,
)

from qgis.utils import iface

from .resources import *
from .analysis_functions import *
from .data_manager import get_number_analysis

import networkx as nx


def get_inputs_from_dialog_service_area(inputs):
    """Service area analysis inputs"""

    dialog = QDialog()
    dialog.setWindowTitle("Service Area Analysis")

    layout = QVBoxLayout()
    dialog.setFixedSize(400, 200)

    label = QLabel("Select the points layer to analyse the service area:")
    layout.addWidget(label)

    # create combo box - layer selection
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
    inputs.time_line_edit.setPlaceholderText("Time (m) [5-60]")
    inputs.time_line_edit.setValidator(QIntValidator(5, 60))
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

    # close the previous dialog
    if starting_dialog:
        starting_dialog.close()
    try:
        points, time, checkbox = get_inputs_from_dialog_service_area(inputs)
    except TypeError:
        return

    crs = QgsProject.instance().crs()

    number_analysis = get_number_analysis()

    service_area_analysis_operations(
        crs, points, time, checkbox, G, G_walk, number_analysis
    )


def create_convex_hull_layer(selected_id_dict: dict, number_analysis: int):
    """Create a layer with the convex hull of the reachable nodes"""
    layers = QgsProject.instance().mapLayers().values()
    service_area_layer = [
        layer for layer in layers if layer.name().startswith("service_area_")
    ]
    layer = service_area_layer[-1]

    fields = QgsFields()
    fields.append(QgsField("ID", QVariant.Int))
    fields.append(QgsField("Area", QVariant.Double))

    convex_hull_layer = QgsVectorLayer(
        "Polygon?crs=" + layer.crs().authid(),
        f"convex_polygons_{number_analysis}",
        "memory",
    )

    convex_hull_layer.dataProvider().addAttributes(fields)
    convex_hull_layer.updateFields()
    convex_hull_layer.startEditing()

    for key_id, selected_id in selected_id_dict.items():
        # deselect all the features
        layer.removeSelection()

        # select only the features with the selected id
        layer.selectByIds(selected_id)

        selected_geometry = None

        for feat in layer.selectedFeatures():
            feature_geometry = feat.geometry()
            if selected_geometry is None:
                selected_geometry = feature_geometry
            else:
                selected_geometry = selected_geometry.combine(feature_geometry)

        # convert the geometry to a convex hull
        convex_hull = selected_geometry.convexHull()
        area = convex_hull.area() * (111**2)  # convert to km^2

        convex_hull_feature = QgsFeature(convex_hull_layer.fields())
        convex_hull_feature.setGeometry(convex_hull)
        convex_hull_feature.setAttributes([key_id, area])

        convex_hull_layer.addFeature(convex_hull_feature)
        layer.removeSelection()

    # print the feature data
    for feature in convex_hull_layer.getFeatures():
        print(feature.attributes())

    convex_hull_layer.commitChanges()

    QgsProject.instance().addMapLayer(convex_hull_layer)


def service_area_analysis_operations(
    crs: QgsCoordinateReferenceSystem,
    points: list,
    time: int,
    checkbox: bool,
    G: nx.DiGraph,
    G_walk: nx.MultiDiGraph,
    number_analysis: int,
):
    """Operations for service area analysis"""
    progress_bar = QProgressDialog()
    progress_bar.setWindowTitle("Service Area Analysis")
    progress_bar.setLabelText("Analysis in progress...")
    progress_bar.setCancelButtonText(None)
    progress_bar.setMinimum(0)
    progress_bar.setMaximum(100)
    progress_bar.setWindowModality(2)
    progress_bar.setValue(0)
    progress_bar.show()
    QApplication.processEvents()

    nearest_nodes = []
    for point in points:
        current_nearest_node = ox.nearest_nodes(G, point[0], point[1])
        nearest_nodes.append(current_nearest_node)

    # TODO: add the id in modo
    create_and_load_layer_starting_points(crs, nearest_nodes, G, number_analysis)

    progress_bar.setValue(20)

    selected_id_dict = create_and_load_layer_reachable_nodes(
        G, crs, nearest_nodes, time, G_walk, checkbox, number_analysis
    )

    progress_bar.setValue(60)

    create_convex_hull_layer(selected_id_dict, number_analysis)

    progress_bar.setValue(100)
