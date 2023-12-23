from qgis.core import (
    QgsMarkerSymbol,
    QgsLineSymbol,
    QgsSingleSymbolRenderer,
    QgsMapLayer,
)

from .resources import *


def change_style_layer(
    layer_name: QgsMapLayer, name: str, color: str, size: str, width: str
):
    """Change style of a layer"""

    # point layer
    if size is not None:
        symbol = QgsMarkerSymbol.createSimple(
            {"name": name, "color": color, "size": size}
        )

    # line layer
    elif width is not None:
        symbol = QgsLineSymbol.createSimple({"color": color, "width": width})

    renderer = QgsSingleSymbolRenderer(symbol)
    layer_name.setRenderer(renderer)


def route_type_to_speed(route_type: int) -> int:
    """Convert route type to speed"""
    # tram
    if route_type == 0:
        return 23
    # subway, metro
    elif route_type == 1:
        return 60
    # rail (long distance travel)
    elif route_type == 2:
        return 160
    # bus
    elif route_type == 3 or route_type == 700 or route_type == 200 or route_type == 702:
        return 25
    # ferry
    elif route_type == 4:
        return 40
    # cable tram
    elif route_type == 5:
        return 23
    # aerial lift
    elif route_type == 6:
        return 20
    # funicular
    elif route_type == 7:
        return 25
    # trolleybus
    elif route_type == 11:
        return 20
    # monorail
    elif route_type == 12:
        return 70
    # walk
    elif route_type == 15:
        return 5
