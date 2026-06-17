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
This repository separates dependencies as follows:
- Python dependencies are declared in `pyproject.toml`.
- Non-Python tooling (Quarto/Pandoc/etc.) is declared in `environment.yml`.

Recommended setup:
1. Create and activate the Conda environment for non-Python tools:
	`conda env create -f environment.yml`
	`conda activate asimviz`
2. Install Python dependencies from `pyproject.toml`:
	`uv sync` or `python -m pip install -e .`

If you prefer not to use Conda, install the non-Python tools manually
for your OS (at minimum `quarto`), then run  (or `python -m pip install -e .`).

## Output Compilation
To build the output website, run the `compile.py` script
(`conda run -n asimviz python`), which
will pull a list of Jupyter notebooks from `_quarto.yml` to
execute. The outputs from these notebooks will be compiled
into the new website, found in the `output` directory.

## Cleaning Notebooks
When compiling the source notebooks, output data and metadata
are generated and stored in the file alongside the source.
In preparation for uploading notebooks to this repository, please remove the output data and metadata to keep the notebooks tidy.
Functionality is included in the `compile.py` script to do this
using the `--clean` command-line argument. For example:
```
python compile.py --clean
```