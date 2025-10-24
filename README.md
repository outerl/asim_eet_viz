# ActivitySim Base-vs.-Build Scenario Comparison Visualizer

This repository contains a set of Jupyter notebooks which
develop summary statistics and charts for visualizing the
comparative results of a base and build scenario. The initial
use case is a bespoke solution for the Explicit Error Terms
project but may be useful for any base-vs.-build scenario
comparison.

## Input Notebooks and Data
The notebooks, stored in the `notebooks` directory, all 
pull base and build data from directories specified in
`_quarto.yml` under the `sources` setting. An example
dataset pair is provided under the `input/example` directory
which acts as the default source in the configuration YAML.
Modify the `sources.base` and `sources.build` settings to
select a different data source.

## Installation
To install the appropriate dependencies for creating the
output visualizations, install the dependencies in the
`environment.yml` file using `conda env create -n {environment_name}`

## Output Compilation
To build the output website, run the `compile.py` script, which
will pull a list of Jupyter notebooks from `_quarto.yml` to
execute. The outputs from these notebooks will be compiled
into the new website, found in the `output` directory.

## Cleaning Notebooks
When compiling the source notebooks, output data and metadata
are generated and stored in the file alongside the source.
In preparation for uploading notebooks to this repository, please 
remove the output data and metadata to keep the notebooks tidy.
Functionality is included in the `compile.py` script to do this
using the `--clean` command-line argument. For example:
```
python compile.py --clean
```

## Summaries
The folder `summaries` includes a series of files providing statistics 
on changes in OD demand across the various scenarios. These files include:

- CSV files detailing the base scenario OD tour demand in the transit and 
  employment scenarios by TAZ and MGRA
- Shapefiles for the transit and employment scenarios with the following fields:
    - `mc_OD`:      the number of tours in each origin TAZ which changed 
                    destination in the Monte Carlo implementation
    - `eet_OD`:     the number of tours in each origin TAZ which changed 
                    destination in the explicit error term implementation
    - `del_dest_M`: the change in total tours destined for each TAZ in the 
                    Monte Carlo implementation
    - `del_dest_E`: the change in total tours destined for each TAZ in the
                    explicit error term implementation
- PDF maps visualizing each of the above fields for each implementation
- A QGIS project file used to construct the maps. The input layers are the
  above shapefiles, and the map layouts are stored in the project's Layout Manager
    - For more information on QGIS projects, see [the QGIS documentation 
      website](https://qgis.org/resources/hub/)