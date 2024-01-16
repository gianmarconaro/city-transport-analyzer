# City Transport Analyzer QGIS Plug-in

QGIS Plugin that analyses the interoperability of urban transport and accessibility within a city using GTFS data.

## Prerequisites
| Library            | Minimum Required Version  |
|--------------------|---------------------------|
| OSMnx              | 1.3.1.post0               |
| Scikit-learn       | 1.3.2                     |
| Shapely            | 2.0.2                     |

## Installation
The plugin uses external libraries that must be installed before using it.

Install them using ***pip*** inside your QGIS environment:

```bash
pip install osmnx scikit-learn shapely
```

Clone the repository:

```bash
git clone url_directory
```

Compress repository folder with .zip.

Then import the plugin into QGIS via .zip file. Go to `Plugins` > `Manage and install Plugin...` > `Install from ZIP` 

## Features

You need a GTFS data source to use the plugin, so download the data for the city you are interested in.

**From the main dashboard is possible to:**


- Import GTFS data
- Import a polygon file containing a list of points that will determine the pedestrian area to be used
- Create the Urban Transit Network Graph starting from GTFS data
- Import/Export Urban Transit Network Graph

After importing all the data, two analyses can be performed based on ***points layer***.

### Interoperability Analysis

This analysis aims to show how the stops in a certain area are interconnected with each other. It is also possible to see the means that serve this area and which stops in the specific.

For each point, find the nearest stop and highlight all the stops in the range defined by the user.

![pt romana - selected stops](https://github.com/gianmarconaro/qgis-plugin/assets/57094315/bae022f1-62d4-4342-abd7-ba4a7494be5e)

**Green squares** = stops \
**Yellow squares** = selected stops \
**Blue square** = starting stop

**For next analyses, only stops that do not share any means with the starting stop are considered!**

The pedestrian path between starting stop and selected stops is calculated.

![pt romana - shortest_paths](https://github.com/gianmarconaro/qgis-plugin/assets/57094315/e563b49b-1b66-46b9-ab5e-370d14efce70)

### Accessibility Analysis

This analysis aims to show the accessibility of an area and how it is connected with the rest of the city showing all the points that can be reached within a given time interval from an initial point using only public transportation.

For each point, the service area is generated.

![pt romana - service area](https://github.com/gianmarconaro/qgis-plugin/assets/57094315/4c1e2a80-c076-4faf-94c7-144513c07fdf)

Then the **convex hull** of the service area is generated.

![pt_romana_convex hull](https://github.com/gianmarconaro/qgis-plugin/assets/57094315/84831cc2-c6f3-4e3e-a19b-b99d83931108)


## Contributing

If you'd like to contribute to this project, follow these steps:

1. Fork the project
2. Create a new branch (`git checkout -b enhancements`)
3. Commit your changes (`git commit -m 'Added a new feature'`)
4. Push the branch (`git push origin enhancements`)
5. Open a new Pull Request

## Issue Reporting

If you find a bug or have a suggestion, please open a new issue [here](https://github.com/gianmarconaro/qgis-plugin/issues).
