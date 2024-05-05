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
    if route_type in [0, 900, 901, 902, 903, 904, 905, 906]:
        return 23
    # subway, metro
    elif route_type in [1, 400, 401, 402, 403, 404]:
        return 60
    # rail (long distance travel)
    elif route_type in [2, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117]:
        return 160
    # bus
    elif route_type in [3, 200, 201, 202, 203, 204, 205, 206, 207, 208, 209, 700, 702, 703, 704, 706, 707, 708, 709, 710, 712, 713]:
        return 25
    # ferry
    elif route_type in [4, 1200]:
        return 40
    # cable tram
    elif route_type == 5:
        return 23
    # aerial lift
    elif route_type == 6:
        return 20
    # funicular
    elif route_type in [7, 1400]:
        return 25
    # trolleybus
    elif route_type in [11, 800]:
        return 20
    # monorail
    elif route_type in [12, 405]:
        return 70
    # long distance bus
    elif route_type in [701, 705, 711, 715, 716]:
        return 100
    # walk
    elif route_type == 15:
        return 5


# def import_libs():
#     import sys
#     import os

#     working_dir = os.path.dirname(os.path.realpath(__file__))
#     lib_folder = os.path.join(working_dir, "lib")

#     for lib in os.listdir(lib_folder):
#         sys.path.append(os.path.join(lib_folder, lib))
    
def import_libs():
    libs = [
        ['osmnx', 'osmnx', '1.8.0'],
        ['shapely', 'shapely', '2.0.2'],
        ['scikit-learn', 'sklearn.neighbors', '1.3.2']
    ]

    for lib, import_name, version in libs:
        try:
            __import__(import_name)
        except ModuleNotFoundError:
            print(f'Module {lib} not found. Installing...')
            from pip._internal import main as pip
            pip(['install', "--ignore-installed", f"{lib}=={version}"])
            __import__(import_name)