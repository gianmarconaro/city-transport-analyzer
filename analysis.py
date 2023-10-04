from qgis.core import QgsProject

from .resources import *

from .analysis_functions import *
from .inputs import Inputs


class Analysis(Inputs):
    def start_analysis(self):
        """Start the analysis process by asking the user the analysis type and then calling the function that does the analysis"""
        project = QgsProject.instance()

        remove_layers(project)

        # crea e carica il layer di debug
        create_debug_layer()

        # ask the user the analysis type
        self.select_analysis_type()
