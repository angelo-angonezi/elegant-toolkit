# elegant-toolkit

Automated image-analysis pipelines for *C. elegans* microscopy data, developed in the [Mango Lab](https://www.biozentrum.unibas.ch/research/research-groups/research-groups-a-z/overview/unit/research-group-susan-mango) at the Biozentrum, University of Basel.

The toolkit takes raw multi-channel microscopy stacks (`.vsi`, `.nd2`, `.ics`, `.tif`) and:

- splits channels and runs optional preprocessing (cropping, padding, blurring, deconvolution);
- segments embryos and nuclei with [Cellpose](https://github.com/MouseLand/cellpose);
- segments sub-nuclear "dot" structures by intensity thresholding or Difference of Gaussians blob detection;
- post-processes the masks (closing, merging, resizing);
- measures every object (morphology, intensity, position, texture, distances) and writes dataframes and summary tables.

The pipeline can be run both via a Graphical User Interface (see installation instructions below)
or directly via the command line.

## Installation

Create a conda environment with Python 3.10 or newer, then install the package from the repository root.

```
conda create -n elegant_toolkit python=3.12
```

### pip install

```
pip install elegant-toolkit
```

### local install

Clone the repo with:

```
git clone https://github.com/angelo-angonezi/elegant-toolkit.git
```

And install with:

(CPU only)

```
pip install .[cpu]
```

(GPU - CUDA 13x)

```
pip install .[gpu] --extra-index-url https://download.pytorch.org/whl/cu130
```

Then run the setup steps below, and check the installation with `cet-version`, `cet-check_gpu` and `cet-check_java`.

**Note:** While the pipelines can theoretically be run on a CPU-only machine, running the scripts with a GPU is highly
recommended, especially with large confocal microscopy data.

## Setup steps

Some dependencies can't be installed with pip, so the package ships `cet-download_*` commands for them. Each one
takes `-h` for its options.

| Command | What it does | When to run it |
|---|---|---|
| `cet-download_jdk` | Installs a JDK (conda-forge `openjdk`) into the active conda env, used by the Bio-Formats readers for `.ics`, `.tif` and `.vsi` files. | Once, unless your env already has a JDK. |
| `cet-download_loci_jar` | Downloads the Bio-Formats `loci_tools.jar` ahead of time. Otherwise it is downloaded silently in the middle of the first `.ics`/`.tif`/`.vsi` conversion. | Optional. |
| `cet-download_cp_models` | Downloads the Cellpose `cpsam` weights to `~/.cet/cellpose/models`, the location the pipeline uses. | Once, before the first segmentation. |
| `cet-download_pycudadecon` | Installs `pycudadecon` from conda-forge, since its PyPI wheel has no working CUDA backend. | GPU installs, if you use deconvolution. |

## Verifying installation and GPU availability

To verify if all pacakges were correctly installed, run:

```
cet-check_imports
```

And to assess GPU availability, run:

```
cet-check_gpu
```
(this verifies GPU-related imports)

And:

```
cet-check_imports
```
(this loads a small matrix in VRAM to verify that PyTorch and CuPy are actually being used)

## Updating without internet access

On a machine without internet access (for example a cluster), the package can be updated in place from a local folder
of versioned snapshots (`YYYY-MM-DD-v1`, `YYYY-MM-DD-v2`, ...):

- `cet-build_update_folder -o <folder>` builds a new snapshot of the repository on a machine that has the git history.
- `cet-update -i <folder>` copies new and changed files from the most recent snapshot over the installed checkout,
  backs up replaced files, and runs `pip install -e .` at the end. Use `--dry-run` to preview the changes.

The GUI has an update button that runs the same command.

## Quick start

Create a desktop shortcut:

```
cet-create_shortcut
```

Or launch the GUI directly from the terminal with:

```
cet-gui
```

Or run the pipeline from the command line. Copy `src/cet/pipelines/settings/default_settings.yaml`, set `base_folder`
and the other fields for your experiment, and run:

```
python -m cet.pipelines.pipeline path/to/settings.yaml
```

Every processing step is also a standalone module. Run `python -m <module> -h` to see its options.

## Commands

`cet-options` lists all commands.

| Group | Commands |
|---|---|
| GUI | `cet-gui`, `cet-napari`, `cet-create_shortcut` |
| Diagnostics | `cet-options`, `cet-version`, `cet-check_imports`, `cet-check_gpu`, `cet-check_java`, `cet-test_gpu` |
| Setup | `cet-update`, `cet-build_update_folder`, `cet-download_cp_models`, `cet-download_jdk`, `cet-download_loci_jar`, `cet-download_pycudadecon` |

## License

BSD-3. See [LICENSE.md](LICENSE.md).
