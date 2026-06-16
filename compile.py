import nbformat
import os
import sys
import shutil
from nbconvert.preprocessors import (
    ClearMetadataPreprocessor,
    ExecutePreprocessor,
    ClearOutputPreprocessor,
)
import nbparameterise as nbparam
import yaml
import pandas as pd

"""
Compile base-vs.-build result visualizations
from ActivitySim output tables, creating
summaries of the changes between two sets
of outputs across the variety of ActivitySim
models.

The compiler first executes the listed Jupyter
notebooks individually, then strips out all
notebook metadata to prepare the executed notebook
for rendering using `quarto`. The render procedure
then creates a set of HTML files from the config
file `_quarto.yml`, with a main page as defined in
`index.qmd` and a separate page for the notebook
itself.
"""


def run_notebooks(
    notebooks: list,
    zone_set: str,
    how_method: str,
    affected_zones,
):

    notebook_execution_resources = {
        "metadata": {"path": os.path.abspath("notebooks")}
    }

    for filename in notebooks:

        print(f"Executing subset {zone_set} notebook {filename}...")

        # open the notebook
        with open(os.path.join("notebooks", filename)) as fi:
            nb_in = nbformat.read(fi, nbformat.NO_CONVERT)

        # overwrite parameters in notebooks
        orig_params = nbparam.extract_parameters(nb_in)
        new_params = nbparam.parameter_values(
            orig_params,
            zone_set=zone_set,
            how_method=how_method,
            affected_tazs=[int(taz) for taz in affected_zones.taz.unique()],
            affected_mazs=[int(maz) for maz in affected_zones.MAZ.unique()],
        )
        """
        In the above, I've attempted to use more direct functionality than
        just copying the entire list into the notebook file, like passing
        lambda functions directly, but it seems the nbparameterize module
        can only handle certain types. Therefore, we create a temporary
        notebook and will need to clean it up after quarto has compiled it.
        Definitely a FIXME but not in scope at moment. 
        
        ~~ W. Alexander 2025-06-04

        """
        nb_in = nbparam.replace_definitions(nb_in, new_params)

        # execute it
        ep = ExecutePreprocessor(timeout=1000, kernel_name="python3")
        ep.preprocess(nb_in, resources=notebook_execution_resources)

        # strip out all metadata that causes issues for Quarto
        cmp = ClearMetadataPreprocessor(timeout=1000, kernel_name="python3")
        # exclude cell tags from removal
        cmp.preserve_cell_metadata_mask |= {"tags"}
        cmp.preprocess(nb_in, resources={})

        # write the file back out, with execution results
        with open(
            os.path.join("notebooks", zone_set, filename), "w", encoding="utf-8"
        ) as fo:
            nbformat.write(nb_in, fo)


def clean(notebooks: list):
    """
    This method cleans all output from the Jupyter notebooks to make
    them more appropriate for committing to the repository.

    Parameters:

        notebook: list      notebook filenames to clean
    """

    for filename in notebooks:

        print(f"Cleaning notebook {filename}...")

        # open the notebook
        with open(f"notebooks/{filename}") as fi:
            nb_in = nbformat.read(fi, nbformat.NO_CONVERT)

        # execute it
        cp = ClearOutputPreprocessor(timeout=600, kernel_name="python3")
        cp.preprocess(nb_in, resources={})

        # write the file back out, with execution results
        with open(f"notebooks/{filename}", "w", encoding="utf-8") as fo:
            nbformat.write(nb_in, fo)


def compile_quartobook(cfg: dict):
    """
    This method compiles a website in book format using
    quarto. First, the config yaml is overwritten to
    include all notebooks we've run, then quarto is called
    directly from the underlying OS. Includes a basic check
    for errors in this system call.

    Parameters:
        cfg: dict   the contents of the _quarto.yml file

    """

    # build book chapters from notebooks and zone systems
    cfg["book"]["chapters"] = [
        "index.qmd",  # required home page
        *[
            {
                "part": f"{zone_system}.qmd",
                "chapters": [
                    f"notebooks/{zone_system}/{notebook}"
                    for notebook in cfg["sources"]["notebooks"]
                ],
            }
            for zone_system in ["all", "affected", "unaffected"]
        ],
    ]

    # write a temporary yaml with compiled notebooks included
    with open("_quarto.yml", mode="w") as fo:
        yaml.dump(cfg, fo, sort_keys=False)

    # combine all notebooks and markdown pages as HTML
    cmd = f"quarto render"
    retval = os.system(cmd)

    if retval != 0:
        raise RuntimeError(f"Quarto exited with return value {retval}")


if __name__ == "__main__":

    # read the required default configuration
    with open("_quarto.yml") as f:
        cfg = yaml.safe_load(f)

    # Read the list of Jupyter notebooks from the Quarto YAML config file
    notebooks = [x for x in cfg["sources"]["notebooks"] if x.endswith(".ipynb")]

    # Remove all output data for uploading to GitHub, etc.
    if "--clean" in sys.argv:
        clean(notebooks)

    else:
        # create a backup of the yaml file since we need to modify it in place
        shutil.copy("_quarto.yml", "_quarto.yml.bak")

        try:
            # Get the set of zones being affected in this book
            assert os.path.exists(
                cfg["sources"]["affected_zones"]
            ), """Missing CSV file containing affected zones"""

            affected_zones = pd.read_csv(cfg["sources"]["affected_zones"])
            how_method = cfg["sources"]["how_method"]

            # run for all three sample sets
            for zone_system in ["all", "affected", "unaffected"]:

                # directory to store temp notebooks
                if not os.path.exists(f"notebooks/{zone_system}"):
                    os.makedirs(f"notebooks/{zone_system}")

                run_notebooks(notebooks, zone_system, how_method, affected_zones)

            # call the quarto renderer
            compile_quartobook(cfg)

        finally:
            # replace _quarto.yml with its original file
            os.replace("_quarto.yml.bak", "_quarto.yml")

            # delete temporary notebooks created in running
            for zone_system in ["all", "affected", "unaffected"]:
                if os.path.exists(f"notebooks/{zone_system}"):
                    shutil.rmtree(f"notebooks/{zone_system}")
