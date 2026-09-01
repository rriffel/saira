<p align="center">
  <img src="pacce/assets/logo.jpg" alt="PACCE Logo" width="220">
</p>

<h1 align="center">PACCE</h1>

<p align="center">
  <strong>Python Algorithm to Compute Continuum and Equivalent widths</strong>
</p>

This is an updated and upgraded version of the PACCE code ([Riffel & Vale, 2011, Ap&SS, 334, 351](https://ui.adsabs.harvard.edu/abs/2011Ap%26SS.334..351R)) written in Python.

PACCE measures spectral indices (equivalent widths and breaks) while handling the most common corrections to spectra—broadening to a specific resolution, correcting for Doppler shift, etc.—and organizes the results in a `pandas` DataFrame that integrates naturally into Python workflows. This allows the same uniform treatment of both observations and models, degrading them to a common resolution and facilitating direct comparison.

Now includes a modern **PyQt5 Graphical User Interface (GUI)** for interactive workflow configuration and batch processing.

---

## Installation

It is recommended to run PACCE in an isolated Python environment (via **Conda** or **Python `venv`**).

### 1. Creating a Virtual Environment

#### Option A: Using Conda / Mamba (Recommended)

```bash
# Create a new environment with Python 3.12 (or >= 3.10)
conda create -n pacce_env python=3.12 -y

# Activate the environment
conda activate pacce_env
```

#### Option B: Using Python `venv`

```bash
# Create a virtual environment
python3 -m venv pacce_env

# Activate the environment:
# Linux / macOS:
source pacce_env/bin/activate

# Windows:
pacce_env\Scripts\activate
```

---

### 2. Installing PACCE

Install directly from GitHub with `pip`:

```bash
# Public repository (or via HTTPS token)
pip install git+https://github.com/rriffel/pacce.git@paccegui

# Private repository (via SSH key)
pip install git+ssh://git@github.com/rriffel/pacce.git@paccegui
```

Or for local development:

```bash
git clone -b paccegui https://github.com/rriffel/pacce.git
cd pacce
pip install -e .
```

### Requirements

- Python ≥ 3.10
- [astropy](https://www.astropy.org/)
- [pandas](https://pandas.pydata.org/)
- [scipy](https://scipy.org/)
- [matplotlib](https://matplotlib.org/)
- [PyQt5](https://pypi.org/project/PyQt5/) (for the graphical interface)

All dependencies are installed automatically by `pip`.

---

## Graphical User Interface (GUI)

PACCE comes with a dedicated desktop graphical interface inspired by modern spectroscopy workflows.

<p align="center">
  <img src="pacce/assets/gui_screenshot.png" alt="PACCE GUI Main Screen" width="900">
</p>

### Launching the GUI

You can launch the GUI using any of the following methods:

```bash
# 1. Console command (after pip installation)
pacce-gui

# 2. Python module execution
python -m pacce

# 3. From within Python
import pacce
pacce.gui()
```

### Key GUI Features

- **Sidebar Navigation**: Quick jumping between configuration panels, instant execution, and configuration saving/loading.
- **Input Modes**:
  - **Table / File List**: Load a pre-defined table with spectrum filenames and per-spectrum properties (`sigma`, `FWHM`, `R`, `z`).
  - **Auto-discover by Extension**: Select a directory and specify a file extension/pattern (e.g. `.txt`, `.dat`, `*.spec`, `*`). The GUI automatically discovers all matching files and displays a live spectrum count.
- **Spectral Resolution Management**: An **"Enable Resolution Correction"** master checkbox gates the whole feature (off by default); when on, freely specify initial and final resolutions in $\sigma$ (km/s), $\text{FWHM}$ (Å), or $R$ ($\lambda/\Delta\lambda$).
- **Physical Validation**: Built-in protection that immediately checks and blocks unphysical convolutions (e.g., attempting to convolve to a higher resolution where $\text{FWHM}_{\text{fin}} < \text{FWHM}_{\text{ini}}$, or enabling resolution correction without at least one initial *and* one final value set).
- **Options & Corrections**: An **"Enable Redshift Correction"** master checkbox gates $z$; also includes Monte Carlo error simulations ($N$), Å-to-magnitude conversions, error propagation, and composite index formulas.
- **Index Selection**: A **"Select Indices…"** dialog lists every index in the chosen `.ind` file with a checkbox, lets you save a custom subset as a new `.ind` file, and automatically unchecks (with a warning if you try to re-check) any index whose *Line Limits* fall outside the wavelength range covered by the spectra you're about to process.
- **Automatic Out-of-Range Check**: If you don't use "Select Indices…" yourself, clicking **Run** still scans the whole batch of spectra once, and — if any indices fall outside the covered range — shows a single confirmation listing exactly which ones will be excluded.
- **Live Logging & Output Table**: Real-time console log (including a run-configuration summary: which corrections are active, with what values, and where every output file is saved) and an interactive results preview table with direct CSV export.
- **Results Plotting**: A **"Plot…"** button on the results table opens a separate window to plot any index (or an expression combining indices, e.g. `Mg2 - Fe5270`) against another, with an **"Error bars"** checkbox that automatically overlays the matching `e_<index>` uncertainties, and a "Save Plot As…" option (PNG/PDF/SVG).
- **State Management**: Save and load complete GUI configurations as `.json` files.

---

## Quick Start (Python API)

### 1. Using a Spectrum List Table

```python
from pacce import pacce

# Measure indices from a table listing the spectra
result = pacce(
    filename='spectra_list.dat',        # ASCII table with 'file' column
    path_to_files='./spectra/',         # Directory containing the spectra
    IndexDefs='Riffel_2019_defs.ind',   # Index definitions file
    output_file='measurements.csv'      # Output table (always written as CSV)
)
```

### 2. Auto-discovering Spectra by Extension (No Table Needed)

You can run PACCE across an entire folder of spectra without creating a list file:

```python
from pacce import pacce

# Automatically find and process all .txt spectra in the directory
result = pacce(
    path_to_files='./spectra/',
    file_extension='.txt',              # e.g., '.txt', '.dat', '*.spec', '*'
    IndexDefs='Riffel_2019_defs.ind',
    output_file='measurements.csv',
    do_resolution=True,                 # required master flag to activate the correction below
    sigma_ini=180.0,                    # Assumed initial sigma = 180 km/s
    sigma_fin=250.0                     # Convolve all to sigma = 250 km/s
)
```

The returned `result` is a `pandas.DataFrame` containing all measured indices and errors, and is also
written to `output_file` in CSV format.

> **Note:** `do_resolution` and `do_redshift` default to `False`. Simply passing `sigma_fin`, `z`,
> etc. has **no effect** unless the corresponding flag is also set to `True` — this applies even if
> the input table already has `sigma`/`FWHM`/`R`/`z` columns. See
> [Resolution Mixing & Validation](#resolution-mixing--validation) below.

### 3. Applying a Redshift Correction

```python
from pacce import pacce

result = pacce(
    path_to_files='./spectra/',
    file_extension='.txt',
    IndexDefs='Riffel_2019_defs.ind',
    output_file='measurements.csv',
    do_redshift=True,
    z=0.05
)
```

### 4. Pre-excluding Indices Outside the Spectra's Wavelength Range

The same check the GUI's "Select Indices…" dialog performs is available as plain functions, so you
can filter an `.ind` file from a script before calling `pacce()`:

```python
from pacce.pacce_wapper import (
    list_spectrum_files, get_spectra_wavelength_range, filter_idx_by_range, write_idx_defs,
)
from pacce.PacceFunctions import read_idx_defs
from pacce import pacce

files = list_spectrum_files(path_to_files='./spectra/', file_extension='.txt')
wave_min, wave_max = get_spectra_wavelength_range('./spectra/', files)

idx_definitions = read_idx_defs('Riffel_2019_defs.ind')
in_range = filter_idx_by_range(idx_definitions, wave_min, wave_max)
print(f"{(~in_range).sum()} of {len(idx_definitions)} indices fall outside "
      f"{wave_min:.1f}-{wave_max:.1f} Å and will be skipped.")

# Option A: save the filtered subset as a new .ind file for reuse
write_idx_defs(idx_definitions, 'defs_in_range.ind', in_range)
result = pacce(path_to_files='./spectra/', file_extension='.txt',
                IndexDefs='defs_in_range.ind', output_file='measurements.csv')

# Option B: pass the filtered array directly, no intermediate file needed
result = pacce(path_to_files='./spectra/', file_extension='.txt',
                IndexDefs=idx_definitions[in_range], output_file='measurements.csv')
```

---

## Terminal Usage

Everything above also runs from a plain terminal — no notebook or IDE required.

### 1. Launching the GUI

```bash
# Console command installed by pip
pacce-gui

# Equivalent module execution
python -m pacce
```

### 2. Running PACCE as a Script

Save any of the API examples above to a `.py` file and run it directly:

```bash
cat > run_pacce.py << 'EOF'
from pacce import pacce

result = pacce(
    path_to_files='./spectra/',
    file_extension='.txt',
    IndexDefs='Riffel_2019_defs.ind',
    output_file='measurements.csv',
    do_resolution=True,
    sigma_ini=180.0,
    sigma_fin=250.0,
)
print(result.head())
EOF

python run_pacce.py
```

With `print_log` left unset (the default), the run-configuration summary and per-spectrum progress
print straight to the terminal, e.g.:

```
Found 12 spectra matching '*.txt' in './spectra/'
============================================================
PACCE run configuration
============================================================
Resolution correction: True
  sigma_ini=180.0  FWHM_ini=None  R_ini=None
  sigma_fin=250.0  FWHM_fin=None  R_fin=None
Redshift correction: False
Output file: measurements.csv (CSV)
============================================================
----------------------------
Doing file spec_001.txt with error
...
Measurements saved to measurements.csv (CSV)
```

### 3. Logging to a File Instead of the Terminal

Pass `print_log='pacce.log'` to redirect that same output to a file (handy for batch jobs run with
`nohup`/`screen`/a scheduler), while `result` is still returned in-process:

```bash
python -c "
from pacce import pacce
pacce(path_to_files='./spectra/', file_extension='.txt',
      IndexDefs='Riffel_2019_defs.ind', output_file='measurements.csv',
      print_log='pacce.log')
"
tail -f pacce.log
```

---

## Input Parameters

| Parameter | Description |
|---|---|
| `filename` | ASCII table listing 1-D spectra. Must contain a `file` column. Can include per-spectrum columns: `sigma`, `FWHM`, `R`, `z`. *(Optional if `file_extension` is used)* |
| `path_to_files` | Directory containing the spectra. Default: `'./'`. |
| `file_extension` | Pattern or extension to auto-discover spectra when `filename` is not provided (e.g., `'.txt'`, `'.dat'`, `'*.spec'`, `'*'`). |
| `IndexDefs` | Path to the index definitions file (`.ind`), **or** an already-loaded structured array (e.g. the output of `read_idx_defs()` filtered by `filter_idx_by_range()`). |
| `output_file` | Path for saving the output measurements table, always written as **CSV** regardless of extension. Default: `'demo.txt'`. |
| `do_resolution` | Master flag (default `False`). Must be `True` for *any* resolution correction to apply — including `sigma`/`FWHM`/`R` columns already present in `filename`'s table. |
| `sigma_ini` / `sigma_fin` | Initial / final velocity dispersion ($\text{km/s}$) for convolution. Only used when `do_resolution=True`. |
| `FWHM_ini` / `FWHM_fin` | Initial / final FWHM ($\text{Å}$) for convolution. Only used when `do_resolution=True`. |
| `R_ini` / `R_fin` | Initial / final resolving power $R = \lambda/\Delta\lambda$. Only used when `do_resolution=True`. |
| `do_redshift` | Master flag (default `False`). Must be `True` for the `z` correction to apply — including a `z` column already present in `filename`'s table. |
| `z` | Global redshift correction to apply before measuring. Only used when `do_redshift=True`. |
| `simulate` | Number of Monte Carlo iterations for error estimation. |
| `error` | If `True`, utilizes the error spectrum (3rd column) for analytical uncertainties. |
| `negative_Ew_to_zero` | If `True`, sets negative equivalent width measurements to zero. |
| `A_to_mag` | List of index names to convert from $\text{Å}$ to magnitudes (e.g. `['Mg1', 'Mg2']`). |
| `compute_idx` | Path to a text file containing composite index expressions (e.g. `MgFe'`), one per line. |
| `print_log` | Path to a text file to redirect standard output log. |
| `path_singleind_plots` | Directory for saving individual diagnostic index plots. |
| `AllIndicesPlot` | Filename for saving a combined multi-panel index plot (e.g. `'all_indices.png'`). |
| `allindices_plot_path` | Directory for saving the combined multi-panel plot. |

---

## Resolution Mixing & Validation

Resolution and redshift corrections are **opt-in**: set `do_resolution=True` and/or `do_redshift=True`
(in the API) or check the matching master checkbox (in the GUI) before they take any effect — this
also applies to `sigma`/`FWHM`/`R`/`z` columns already present in an input table, which are otherwise
ignored.

The resolution parameters (`sigma`, `FWHM`, `R`) can be mixed freely—for example, providing `FWHM_ini` together with $\sigma_{\text{fin}}$, or $R_{\text{ini}}$ with $\sigma_{\text{fin}}$.

PACCE converts all resolution units internally into wavelength-dependent $\text{FWHM}(\lambda)$ in Ångströms:
- **From $\sigma$ (km/s)**: $\text{FWHM}(\lambda) = \left(\frac{\sigma \cdot 2.355}{c}\right) \cdot \lambda$
- **From $R$ ($\lambda/\Delta\lambda$)**: $\text{FWHM}(\lambda) = \frac{\lambda}{R}$

### Physical Validation
Spectral convolution can only **degrade/broaden** resolution. PACCE automatically validates resolution settings both in the Python API and the GUI:
- If `do_resolution=True` but no value greater than zero is set in at least one of `sigma_ini`/`FWHM_ini`/`R_ini` **and** at least one of `sigma_fin`/`FWHM_fin`/`R_fin` (as a parameter or a table column), a clear `ValueError` is raised (the GUI shows a dialog instead). The same applies to `do_redshift=True` without any `z` value available.
- If target resolution is higher than initial resolution ($\text{FWHM}_{\text{fin}} < \text{FWHM}_{\text{ini}}$, $\sigma_{\text{fin}} < \sigma_{\text{ini}}$, or $R_{\text{fin}} > R_{\text{ini}}$), the code raises a clear `ValueError` and the GUI blocks execution with a detailed warning.

### Run Configuration Summary
Every run prints a short summary as the first thing in the log (to the terminal, to `print_log`'s
file, or to the GUI's Run Log console) stating whether each correction is active and with what
values, followed by where every output (measurements table, log, plots) is being saved:

```
============================================================
PACCE run configuration
============================================================
Resolution correction: True
  sigma_ini=180.0  FWHM_ini=None  R_ini=None
  sigma_fin=250.0  FWHM_fin=None  R_fin=None
Redshift correction: False
Output file: measurements.csv (CSV)
============================================================
```

---

## Index Definitions File

The definitions file is pipe-delimited (`|`) with four columns:

```
# Name     Line                    RedCont                BlueCont                Ref.
Mgb  |  5160.1250-5192.6250  |  5142.6250-5161.3750, 5191.3750-5206.3750  |  (Trager+98)
```

- **Name**: Index identifier
- **Line**: Wavelength range of the feature (set both limits equal for a break index)
- **Continuum bands**: Comma-separated pairs of wavelength ranges for the continuum fit
- **Ref.**: Literature reference

Pre-configured definition files are bundled in `pacce/suport_files/` (`Riffel_2019_defs.ind`, `less_defs.ind`).

---

## Excluding Out-of-Range Indices (GUI)

A generic `.ind` file often mixes indices from different spectral ranges (optical + near-IR, for
example). Measuring an index whose *Line Limits* fall outside a spectrum's wavelength coverage fails
for that spectrum and shows up as `NaN` in the results.

- **Automatic check**: clicking **Run** scans the wavelength coverage across the whole batch of
  spectra once (not once per spectrum) and, if any indices fall outside it, shows a single
  confirmation dialog listing exactly which ones will be excluded before proceeding.
- **Manual control**: the **"Select Indices…"** button (next to the Index Definitions combo box)
  opens a checklist of every index in the file. Indices outside the batch's wavelength range start
  unchecked; checking one back on shows a warning but still allows the override. **"Save Selection
  As…"** writes the checked subset out as a new `.ind` file for reuse.

The same logic is available from a script — see
[§4 Pre-excluding Indices Outside the Spectra's Wavelength Range](#4-pre-excluding-indices-outside-the-spectras-wavelength-range) above.

---

## Plotting Results (GUI)

Once a run finishes, the **"Plot…"** button above the Results Preview table opens a separate window:

- Choose **X** and **Y** from a dropdown of index names, or type an expression combining several of
  them (e.g. `Mg2 - Fe5270`, `log10(Hbeta)`). Wrap names containing dots or dashes in backticks, e.g.
  `` `NaI1.14` / Mg2 ``. The `e_<index>` error columns are not listed as plottable variables.
- Check **"Error bars"** to automatically overlay the matching `e_<index>` uncertainty for whichever
  axis is set to a plain index name (an axis using an expression is plotted without error bars, since
  there is no single matching error column for it).
- **"Save Plot As…"** exports the figure as PNG, PDF, or SVG.

---

## Error Handling

PACCE supports two approaches for error estimation:

1. **Analytical (default when error spectrum exists)**: Estimates errors from the S/N ratio in the feature and continuum bands using the formalism of [Cardiel et al. (2006)](https://arxiv.org/abs/astro-ph/0606341).
2. **Monte Carlo (`simulate=N`)**: Generates $N$ synthetic spectra from the observed spectrum and error array, re-measures the indices, and derives the uncertainty from the standard deviation.

---

## Variable-Sigma Convolution

PACCE performs spectral convolution with a variable-sigma Gaussian kernel using the Fourier-space algorithm described in [Cappellari (2022)](https://ui.adsabs.harvard.edu/abs/2022arXiv220814974C). This handles wavelength-dependent resolution differences properly, including error propagation following [Klein (2021)](https://ui.adsabs.harvard.edu/abs/2021RNAAS...5...39K).

---

## Examples

Two Jupyter notebooks are provided in the repository:

- **`Examples.ipynb`** — Demonstrates the full API: basic index measurement, spectral convolution, magnitude conversion, composite indices, MC error estimation, and diagnostic plotting.
- **`Models_and_obs.ipynb`** — Practical use case: measuring indices in SDSS spectra and E-MILES models at a common resolution, then deriving ages and metallicities via grid interpolation.

---

## Project Structure

```
pacce/
├── pacce/
│   ├── __init__.py              # Package entry point (exports pacce, PacceFunctions, and gui())
│   ├── __main__.py              # CLI launcher (python -m pacce)
│   ├── PacceFunctions.py        # Core algorithms (eqw, varsmooth, plotting, etc.)
│   ├── pacce_wapper.py          # High-level wrapper function (table & auto-discovery)
│   ├── pacce_run.py             # Example script
│   ├── assets/                  # Branding and UI assets (logo.jpg)
│   ├── gui/                     # PyQt5 Graphical Interface
│   │   ├── __init__.py
│   │   ├── constants.py         # UI themes and styling
│   │   ├── custom_widgets.py    # Reusable controls & console
│   │   ├── main_gui.py          # Main application window & background worker
│   │   ├── index_selection_dialog.py  # "Select Indices…" checklist dialog
│   │   └── plot_dialog.py       # "Plot…" results window (with error bars)
│   ├── suport_files/            # Index definitions and spectral resolution data
│   └── examples/                # SDSS spectra, MILES models, and example tables
├── Examples.ipynb               # Tutorial notebook
├── Models_and_obs.ipynb         # Models vs. observations notebook
├── pyproject.toml               # Build configuration and console scripts
├── setup.py                     # Setup script
└── README.md
```

---

## Citation

If you use PACCE in your research, please cite:

> Riffel, R. & Vale, T. B., 2011, Ap&SS, 334, 351

---

## License

This project is open source. See the repository for details.
