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

# TODO: Test and complete


def get_inputs_from_dialog_key_points(inputs):
    """Key points analysis inputs"""

    dialog = QDialog()
    dialog.setWindowTitle("Key Points Analysis")

    layout = QVBoxLayout()
    dialog.setFixedSize(400, 300)

    label = QLabel("Select the points layer to analyse the key points:")
    layout.addWidget(label)

    layers = QgsProject.instance().mapLayers()

    # function to update the fields combo box after that the layer combo box has been changed
    def update_fields_combo_box():
        """Funzione per aggiornare il menu a tendina dei campi in base al layer selezionato"""
        layer_name = inputs.layers_combo_box.currentText()
        layer = QgsProject.instance().mapLayersByName(layer_name)[0]
        fields = layer.fields()
        field_names = [field.name() for field in fields]

        if len(field_names) == 0:
            inputs.field_combo_box.clear()
            inputs.field_combo_box.addItem("No fields found")
            inputs.field_combo_box.setDisabled(True)
        else:
            inputs.field_combo_box.clear()
            inputs.field_combo_box.addItems(field_names)
            inputs.field_combo_box.setDisabled(False)

    # create combo box - starting layer selection
    vector_layers = []
    active_vector_layers_names = []

    for layer in layers.values():
        if layer.type() == QgsMapLayer.VectorLayer:
            vector_layers.append(layer)

    for layer in vector_layers:
        if layer.geometryType() == QgsWkbTypes.PointGeometry:
            active_vector_layers_names.append(layer.name())

    inputs.layers_combo_box = QComboBox()
    inputs.layers_combo_box.addItems(active_vector_layers_names)
    inputs.layers_combo_box.setPlaceholderText("Points Layer")
    inputs.layers_combo_box.setEditable(True)
    inputs.layers_combo_box.setMaxVisibleItems(5)

    # define compleater
    compleater = QCompleter(active_vector_layers_names)
    compleater.setCaseSensitivity(Qt.CaseInsensitive)

    inputs.layers_combo_box.setCompleter(compleater)
    layout.addWidget(inputs.layers_combo_box)

    inputs.layers_combo_box.currentIndexChanged.connect(update_fields_combo_box)

    # create combo box - point layer selection
    target_label = QLabel("Select the target layer:")
    layout.addWidget(target_label)

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

    # create combo box - field selection
    field_label = QLabel("Select the field to analyse:")
    layout.addWidget(field_label)

    layer_name = inputs.points_combo_box.currentText()
    layer = QgsProject.instance().mapLayersByName(layer_name)[0]
    fields = layer.fields()
    field_names = [field.name() for field in fields]

    # if layer has no fields generate a message in the box
    if len(field_names) == 0:
        inputs.field_combo_box = QComboBox()
        inputs.field_combo_box.setPlaceholderText("No fields found")
        inputs.field_combo_box.setEditable(False)
        inputs.field_combo_box.setMaxVisibleItems(5)
        layout.addWidget(inputs.field_combo_box)

    inputs.field_combo_box = QComboBox()
    inputs.field_combo_box.addItems(field_names)
    inputs.field_combo_box.setPlaceholderText("Select a layer")
    inputs.field_combo_box.setEditable(True)
    inputs.field_combo_box.setMaxVisibleItems(5)

    # define compleater
    compleater = QCompleter(field_names)
    compleater.setCaseSensitivity(Qt.CaseInsensitive)

    inputs.field_combo_box.setCompleter(compleater)
    layout.addWidget(inputs.field_combo_box)

    # create the line edit
    range_label = QLabel("Insert the range of the key points analysis:")
    layout.addWidget(range_label)

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
        return get_inputs_from_dialog_key_points(inputs)

    points = []
    layer_name = inputs.points_combo_box.currentText()
    points_layer = QgsProject.instance().mapLayersByName(layer_name)[0]
    for feature in points_layer.getFeatures():
        points.append(feature.geometry().asPoint())
    range = inputs.range_line_edit.text()
    attribute = inputs.field_combo_box.currentText()

    first_layer_name = inputs.layers_combo_box.currentText()
    second_layer_name = inputs.points_combo_box.currentText()

    # manage errors
    handle_key_points_input_errors(inputs, range, attribute, second_layer_name)
    
    return points, first_layer_name, int(range), attribute


def handle_key_points_input_errors(inputs, range, attribute, second_layer_name):
    """Manage errors for nearby stops"""

    # check if the range is within the range
    if range == "":
        iface.messageBar().pushMessage(
            "Error",
            "Range must be within the range",
            level=Qgis.Critical,
            duration=5,
        )
        return get_inputs_from_dialog_key_points(inputs)
    
    if attribute == "":
        iface.messageBar().pushMessage(
            "Error",
            "Attribute must be selected",
            level=Qgis.Critical,
            duration=5,
        )
        return get_inputs_from_dialog_key_points(inputs)
    
    # check if the second layer contains the attribute in the fileds
    layer = QgsProject.instance().mapLayersByName(second_layer_name)[0]
    fields = layer.fields()
    field_names = [field.name() for field in fields]
    if attribute not in field_names:
        iface.messageBar().pushMessage(
            "Error",
            "The selected attribute is not in the target layer",
            level=Qgis.Critical,
            duration=5,
        )
        return get_inputs_from_dialog_key_points(inputs)


def start_key_points_analysis(
    inputs, starting_dialog: QInputDialog, _, G_walk: nx.MultiDiGraph
):
    """Start the key points analysis"""
    if starting_dialog:
        starting_dialog.close()

    try:
        points, layer_name, range, attribute = get_inputs_from_dialog_key_points(inputs)
    except TypeError:
        return

    crs = QgsProject.instance().crs()

    number_analysis = get_number_analysis()
    key_points_analysis_operations(
        inputs, crs, points, layer_name, range, attribute, G_walk, number_analysis
    )


def key_points_analysis_operations(
    inputs,
    crs: QgsCoordinateReferenceSystem,
    points: list,
    layer_name: str,
    range: int,
    attribute: str,
    G_walk: nx.MultiDiGraph,
    number_analysis: int,
):
    """Operations for the key points analysis"""
    progress_bar = QProgressDialog()
    progress_bar.setWindowTitle("Key Points Analysis")
    progress_bar.setLabelText("Analysing...")
    progress_bar.setCancelButtonText("Cancel")
    progress_bar.setMinimum(0)
    progress_bar.setMaximum(100)
    progress_bar.setWindowModality(2)
    progress_bar.setValue(0)
    print(layer_name)

    # create a spatial index for the points layer
    points_layer = QgsProject.instance().mapLayersByName(layer_name)[0]
    layer_index = QgsSpatialIndex(points_layer.getFeatures())

    progress_bar.show()
    QApplication.processEvents()

    # check if the layer has an ID attribute
    has_id = False
    for field in points_layer.fields():
        if field.name().casefold() == "id":
            id_column = field.name()
            has_id = True
            break

    nearest_key_point_ids = []
    for point in points:
        nearest_key_point = layer_index.nearestNeighbor(point, 1)[0]
        key_point_feature = points_layer.getFeature(nearest_key_point)

        if has_id:
            current_key_point_id = key_point_feature[id_column]
        else:
            current_key_point_id = key_point_feature.id()

        current_key_point_attribute = key_point_feature[attribute]

        current_key_point = key_point_feature.geometry().asPoint()
        nearest_key_point_ids.append(
            [current_key_point_id, current_key_point_attribute, current_key_point]
        )

    create_and_load_layer_starting_key_point(
        crs, nearest_key_point_ids, number_analysis
    )

    progress_bar.setValue(20)

    # TODO: from here

    circular_buffer_list = calculate_circular_buffers_key_points(
        nearest_key_point_ids, points_layer, range
    )

    progress_bar.setValue(40)

    (
        nearest_key_point_information,
        selected_key_points_ids,
        selected,
    ) = create_and_load_layer_selected_key_points(
        crs,
        points_layer,
        circular_buffer_list,
        attribute,
        nearest_key_point_ids,
        number_analysis,
    )

    create_and_load_layer_circular_buffer_key_point(
        crs, nearest_key_point_information, number_analysis
    )

    progress_bar.setValue(60)

    # if selected:
    #     create_and_load_layer_shortest_paths(
    #         crs,
    #         nearest_key_point_ids,
    #         selected_key_points_ids,
    #         G_walk,
    #         number_analysis,
    #     )

    progress_bar.setValue(80)


def create_and_load_layer_starting_key_point(
    crs: QgsCoordinateReferenceSystem,
    nearest_key_point: list,
    number_analysis: int,
):
    """Create and load the starting key point layer"""

    project = QgsProject.instance()

    fields = QgsFields()
    fields.append(QgsField("ID", QVariant.Int))
    fields.append(QgsField("Function", QVariant.String))

    starting_key_point_layer = QgsVectorLayer(
        "Point?crs=" + crs.authid(), f"starting_key_points_{number_analysis}", "memory"
    )

    starting_key_point_layer.dataProvider().addAttributes(fields)
    starting_key_point_layer.startEditing()

    for key_point in nearest_key_point:
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPointXY(key_point[2]))
        feature.setAttributes([key_point[0], key_point[1]])
        starting_key_point_layer.dataProvider().addFeatures([feature])

    starting_key_point_layer.commitChanges()

    change_style_layer(starting_key_point_layer, "square", "blue", "2", None)

    project.addMapLayer(starting_key_point_layer)


def create_and_load_layer_selected_key_points(
    crs: QgsCoordinateReferenceSystem,
    points_layer: QgsVectorLayer,
    circular_buffer_list: list,
    attribute: str,
    key_points: list,
    number_analysis: int,
):
    """Create and load the selected key points layer"""

    selected_key_points_dict = defaultdict(list)
    selected = False

    project = QgsProject.instance()

    fields = QgsFields()
    fields.append(QgsField("start_ID", QVariant.Int))
    fields.append(QgsField("Selected", QVariant.Int))
    fields.append(QgsField(f"target_{attribute}", QVariant.String))
    fields.append(QgsField(f"starting_{attribute}", QVariant.String))

    (
        total_key_points_list,
        selected_key_points_list,
        discarded_key_points_list,
        key_point_id_list,
    ) = ([], [], [], [])

    selected_key_points_layer = QgsVectorLayer(
        "Point?crs=" + crs.authid(), f"selected_key_points_{number_analysis}", "memory"
    )

    selected_key_points_layer.dataProvider().addAttributes(fields)
    selected_key_points_layer.startEditing()

    key_point_index = QgsSpatialIndex(points_layer.getFeatures())

    for circular_buffer, key_point in zip(circular_buffer_list, key_points):
        intersecting_key_points_ids = key_point_index.intersects(
            circular_buffer.boundingBox()
        )
        starting_key_point_id = key_point[0]

        selected_key_points, discarded_key_points = 0, 0

        for point in intersecting_key_points_ids:
            point_feature = points_layer.getFeature(point)
            point_geometry = point_feature.geometry()

            key_point_id_list.append(point_feature.id())

            if circular_buffer.contains(point_geometry):
                feature = QgsFeature(selected_key_points_layer.fields())
                feature.setGeometry(point_geometry)

                # if the column with the attribute is equal to the attribute of the starting key point, then it is a selected key point
                if point_feature[attribute] != key_point[1]:
                    feature.setAttributes(
                        [
                            starting_key_point_id,
                            0,
                            point_feature[attribute],
                            key_point[1],
                        ]
                    )
                    discarded_key_points += 1
                else:
                    feature.setAttributes(
                        [
                            starting_key_point_id,
                            1,
                            point_feature[attribute],
                            key_point[1],
                        ]
                    )
                    selected_key_points += 1

                    selected = True

                    selected_key_points_dict[starting_key_point_id].append(
                        [feature.id(), feature[f"starting_{attribute}"], key_point]
                    )
                selected_key_points_layer.dataProvider().addFeatures([feature])

        total_key_points_list.append(selected_key_points + discarded_key_points)
        selected_key_points_list.append(selected_key_points)
        discarded_key_points_list.append(discarded_key_points)

    selected_key_points_layer.commitChanges()

    change_style_layer(selected_key_points_layer, "square", "yellow", "2", None)

    project.addMapLayer(selected_key_points_layer)

    nearest_key_points_information = [
        circular_buffer_list,
        key_point_id_list,
        total_key_points_list,
        selected_key_points_list,
        discarded_key_points_list,
    ]

    return nearest_key_points_information, selected_key_points_dict, selected


def calculate_circular_buffers_key_points(
    key_points: list, points_layer: str, range: int
):
    """Calculate the circular buffers for the key points analysis"""
    project = QgsProject.instance()

    circular_buffer_list = []

    for key_point in key_points:
        x_coord = key_point[2][0]
        y_coord = key_point[2][1]

        starting_point = QgsPointXY(x_coord, y_coord)
        starting_point_geometry = QgsGeometry.fromPointXY(starting_point)

        # create distance area
        distance_area = QgsDistanceArea()
        distance_area.setSourceCrs(points_layer.crs(), project.transformContext())
        distance_area.setEllipsoid(project.ellipsoid())

        distance_degrees = distance_area.convertLengthMeasurement(
            range, QgsUnitTypes.DistanceDegrees
        )

        # create a circular buffer
        circular_buffer = starting_point_geometry.buffer(distance_degrees, segments=32)
        circular_buffer_list.append(circular_buffer)

    return circular_buffer_list


def create_and_load_layer_circular_buffer_key_point(
    crs: QgsCoordinateReferenceSystem,
    nearest_key_point_information: list,
    number_analysis: int,
):
    """Create and load the circular buffer layer"""

    (
        circular_buffer_list,
        key_point_id_list,
        total_key_points_list,
        selected_key_points_list,
        discarded_key_points_list,
    ) = nearest_key_point_information

    project = QgsProject.instance()

    fields = QgsFields()
    fields.append(QgsField("ID", QVariant.Int))
    fields.append(QgsField("Key Point", QVariant.Int))
    fields.append(QgsField("Total Key Points", QVariant.Int))
    fields.append(QgsField("Selected Key Points", QVariant.Int))
    fields.append(QgsField("Discarded Key Points", QVariant.Int))

    circular_buffer_layer = QgsVectorLayer(
        "Polygon?crs=" + crs.authid(), f"circular_buffer_{number_analysis}", "memory"
    )

    circular_buffer_layer.dataProvider().addAttributes(fields)
    circular_buffer_layer.startEditing()

    for circular_buffer, key_point_id, total_key_points, selected_key_points, discarded_key_points in zip(
        circular_buffer_list, key_point_id_list, total_key_points_list, selected_key_points_list, discarded_key_points_list
    ):
        feature = QgsFeature()
        feature.setGeometry(circular_buffer)
        feature.setAttributes(
            [
                circular_buffer_list.index(circular_buffer),
                key_point_id,
                total_key_points,
                selected_key_points,
                discarded_key_points,
            ]
        )
        circular_buffer_layer.dataProvider().addFeatures([feature])

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

    circular_buffer_layer.commitChanges()

    project.addMapLayer(circular_buffer_layer)
