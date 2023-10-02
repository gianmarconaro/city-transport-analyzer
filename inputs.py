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
        layout = QVBoxLayout()

        dialog.setFixedSize(300, 150)

        label = QLabel("Select the type of analysis you want to perform:")

        button_service_area = QPushButton("Service Area")
        button_nearby_stops = QPushButton("Nearby Stops")
        button_both_analyses = QPushButton("Both Analyses")

        button_service_area.setToolTip(
            "Find the service area starting from\na stop with a custom time limit"
        )
        button_nearby_stops.setToolTip(
            "Find the shortest paths between a starting stop and all\nthe other stops in the city that are in a certain distance limit"
        )
        button_both_analyses.setToolTip(
            "Find the service area starting from a stop with a custom time limit\nand find the shortest paths between a starting stop and all\nthe other stops in the city that are in a certain distance limit"
        )

        layout.addWidget(label)
        layout.addWidget(button_service_area)
        layout.addWidget(button_nearby_stops)
        layout.addWidget(button_both_analyses)

        dialog.setLayout(layout)
        dialog.setWindowTitle("Type Analysis")

        # connect the buttons to the functions
        button_service_area.clicked.connect(
            lambda: start_service_area_analysis(self, dialog, *self.load_graphs())
        )
        button_nearby_stops.clicked.connect(
            lambda: start_nearby_stops_paths_analysis(self, dialog, *self.load_graphs())
        )
        button_both_analyses.clicked.connect(
            lambda: start_multi_analysis(self, dialog, *self.load_graphs())
        )

        dialog.exec_()

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
