from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
)

from .resources import *

from .service_area_analysis import *
from .nearby_stops_paths_analysis import *
from .multi_analysis import *

import networkx as nx
import osmnx as ox

G = None
G_WALK = None


class Inputs:
    def select_analysis_type(self):
        """Create a dialog that ask the user with 3 different buttons which analysis he wants to do and put a comment beside each button explaining what the analysis does"""
        dialog = QDialog()
        dialog.setWindowTitle("Analysis type")

        layout = QVBoxLayout()
        dialog.setFixedSize(400, 150)

        label = QLabel("Select the analysis type")
        layout.addWidget(label)

        # create in column two checkbox with the analysis type
        # create the first checkbox
        self.service_area_checkbox = QCheckBox("Service Area Analysis")
        self.service_area_checkbox.setChecked(False)
        layout.addWidget(self.service_area_checkbox)

        # create the second checkbox
        self.nearby_stops_checkbox = QCheckBox("Nearby Stops Analysis")
        self.nearby_stops_checkbox.setChecked(False)
        layout.addWidget(self.nearby_stops_checkbox)

        # create the run button
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # add the layout to the dialog
        dialog.setLayout(layout)

        # run the dialog
        result = dialog.exec_()
        if result == QDialog.Accepted:
            if (
                self.service_area_checkbox.isChecked()
                and not self.nearby_stops_checkbox.isChecked()
            ):
                start_service_area_analysis(self, dialog, *self.load_graphs())
            if (
                self.nearby_stops_checkbox.isChecked()
                and not self.service_area_checkbox.isChecked()
            ):
                start_nearby_stops_paths_analysis(self, dialog, *self.load_graphs())
            if (
                self.service_area_checkbox.isChecked()
                and self.nearby_stops_checkbox.isChecked()
            ):
                start_multi_analysis(self, dialog, *self.load_graphs())
        else:
            return

    def load_graphs(self):
        print("Loading graphs...")

        global G, G_WALK

        GRAPH_PATH_GML_WALK = self._path + "/graphs/pedestrian_graph.graphml"
        GRAPH_PATH_GML_ROUTE = self._path + "/graphs/routes_graph.graphml"

        G_WALK = G_WALK or ox.load_graphml(
            GRAPH_PATH_GML_WALK,
            node_dtypes={"fid": int, "osmid": str, "x": float, "y": float},
            edge_dtypes={
                "fid": int,
                "u": str,
                "v": str,
                "key": int,
                "weight": float,
                "transport": str,
                "from": str,
                "to": str,
            },
        )

        G = G or nx.read_graphml(GRAPH_PATH_GML_ROUTE)

        print("Graphs loaded")
        return G, G_WALK
