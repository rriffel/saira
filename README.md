# PACCE

**Python Algorithm to Compute Continuum and Equivalent widths**

This is an updated and upgraded version of the PACCE code (Riffel & Vale, 2011, Ap&SS.334..351) written in Python.

PACCE measures spectral indices (equivalent widths and breaks) while handling the most common corrections to spectra—broadening to a specific resolution, correcting for Doppler shift, etc.—and organizes the results in a `pandas` DataFrame that integrates naturally into Python workflows. This allows the same uniform treatment of both observations and models, degrading them to a common resolution and facilitating direct comparison.

## Installation

Install directly from GitHub with `pip`:

```bash
pip install git+https://github.com/rriffel/pacce.git
```

### Requirements

- Python ≥ 3.10
- [astropy](https://www.astropy.org/)
- [pandas](https://pandas.pydata.org/)
- [scipy](https://scipy.org/)
- [matplotlib](https://matplotlib.org/)

All dependencies are installed automatically by `pip`.

## Quick Start

```python
from pacce import pacce

# Measure indices from a list of spectra
result = pacce(
    filename='spectra_list.dat',        # ASCII table listing the spectra
    path_to_files='./spectra/',         # directory containing the spectra
    IndexDefs='index_definitions.ind',  # index definitions file
    output_file='measurements.txt'      # output table
)
```

The returned `result` is a `pandas.DataFrame` with all measured indices and errors.

## Input Parameters

| Parameter | Description |
|---|---|
| `filename` | ASCII table listing the 1-D spectra to measure. Must contain a `file` column. Can also include `sigma`, `FWHM`, `R`, and `z` columns to provide per-spectrum values. |
| `path_to_files` | Path to the directory containing the spectra listed in `filename`. |
| `IndexDefs` | Path to the ASCII file defining the indices to measure (see format below). |
| `output_file` | Path for saving the output table with measurements. |
| `sigma_ini` / `sigma_fin` | Initial / final velocity dispersion (km/s) for spectral convolution. |
| `FWHM_ini` / `FWHM_fin` | Initial / final FWHM (Å) for spectral convolution. |
| `R_ini` / `R_fin` | Initial / final spectral resolution R = λ/Δλ. |
| `z` | Redshift correction to apply before measuring. |
| `simulate` | Number of Monte Carlo iterations for error estimation. |
| `A_to_mag` | List of index names to convert from Å to magnitudes (e.g. `['Mg2', 'Mg1']`). |
| `compute_idx` | Path to a text file with composite index expressions (e.g. `MgFe'`), one per line. |
| `print_log` | Path to a log file to redirect diagnostic output. |
| `path_singleind_plots` | Directory for saving individual index plots. |
| `AllIndicesPlot` | Filename for the combined all-indices plot. |
| `allindices_plot_path` | Directory for saving the combined all-indices plot. |
| `negative_Ew_to_zero` | If `True`, sets negative EW measurements to zero. |

The resolution parameters (`sigma`, `FWHM`, `R`) can be mixed freely—for instance, you can provide `FWHM_ini` together with `sigma_fin`. If a column named `sigma`, `FWHM`, `R`, or `z` exists in the input table, its values are used per-spectrum (overriding global keywords), which is useful when dealing with data of varying resolution.

## Index Definitions File

The definitions file is pipe-delimited (`|`) with four columns:

```
# Name     Line                    RedCont                BlueCont                Ref.
Mgb  |  5160.1250-5192.6250  |  5142.6250-5161.3750, 5191.3750-5206.3750  |  (Trager+98)
```

- **Name**: index identifier
- **Line**: wavelength range of the feature (set both limits equal for a break index)
- **Continuum bands**: comma-separated pairs of wavelength ranges for the continuum fit
- **Ref.**: literature reference

Example files are included in `pacce/suport_files/`.

## Error Handling

PACCE supports two approaches for error estimation:

1. **Analytical (default when error spectrum exists)**: Estimates errors from the S/N ratio in the absorption feature using the formalism of [Cardiel et al. (2006)](https://arxiv.org/abs/astro-ph/0606341).
2. **Monte Carlo (`simulate=N`)**: Generates `N` mock spectra from the observed spectrum and its errors, re-measures the indices, and uses the standard deviation as the uncertainty. More robust but slower.

If the input spectra contain a third column (wavelength, flux, error), errors are computed automatically.

## Variable-Sigma Convolution

PACCE performs spectral convolution with a variable-sigma Gaussian kernel using the Fourier-space algorithm described in [Cappellari (2022)](https://ui.adsabs.harvard.edu/abs/2022arXiv220814974C). This handles wavelength-dependent resolution differences properly, including error propagation following [Klein (2021)](https://ui.adsabs.harvard.edu/abs/2021RNAAS...5...39K).

## Examples

Two Jupyter notebooks are provided in the repository root:

- **`Examples.ipynb`** — Demonstrates the full API: basic index measurement, spectral convolution, magnitude conversion, composite indices, MC error estimation, and diagnostic plotting.
- **`Models_and_obs.ipynb`** — A practical use-case: measuring indices in SDSS spectra and E-MILES models at a common resolution, then deriving ages and metallicities via grid interpolation.

Both notebooks use example data bundled in `pacce/examples/`.

## Project Structure

```
pacce/
├── pacce/
│   ├── __init__.py              # Package init (exports pacce and PacceFunctions)
│   ├── PacceFunctions.py        # Core functions (eqw, varsmooth, plotting, etc.)
│   ├── pacce_wapper.py          # High-level wrapper function
│   ├── pacce_run.py             # Example script
│   ├── suport_files/            # Index definitions and spectral resolution data
│   └── examples/                # SDSS spectra, MILES models, and example tables
├── Examples.ipynb               # Tutorial notebook
├── Models_and_obs.ipynb         # Models vs. observations notebook
├── pyproject.toml               # Build configuration
├── setup.py                     # Setup script (backward compatibility)
└── README.md
```

## Citation

If you use PACCE in your research, please cite:

> Riffel, R. & Vale, T. B., 2011, Ap&SS, 334, 351

## License

This project is open source. See the repository for details.
