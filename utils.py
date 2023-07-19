from qgis.core import QgsMarkerSymbol, QgsLineSymbol, QgsSingleSymbolRenderer, QgsMapLayer

from .resources import *

def change_style_layer(layer_name: QgsMapLayer, name: str, color: str, size: str, width: str):
    """Change style of a layer"""

    # if is a point layer
    if size is not None:
        symbol = QgsMarkerSymbol.createSimple({'name': name, 'color': color, 'size': size})
    
    # if is a line layer
    elif width is not None:
        symbol = QgsLineSymbol.createSimple({'color': color, 'width': width})

    renderer = QgsSingleSymbolRenderer(symbol)
    layer_name.setRenderer(renderer)