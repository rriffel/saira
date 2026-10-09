<p align="center">
  <img src="saira/assets/logo.jpeg" alt="SAIRA Logo" width="220">
</p>

<h1 align="center">SAIRA</h1>

<p align="center">
  <strong>Self-consistent Algorithm for spectral Indices measuRements and Analysis</strong>
</p>

SAIRA measures spectral indices — equivalent widths and breaks — on 1-D spectra, and takes care of
the boring-but-important bits along the way: broadening spectra to a common resolution, correcting
for redshift, propagating errors. Everything comes back as a `pandas` DataFrame, so it drops straight
into whatever Python workflow you're already using. Because observations and models can be degraded
to the same resolution before measuring, you can compare the two directly instead of fighting with
unit conversions and ad-hoc scripts every time.

SAIRA is a Python rewrite and extension of PACCE, our original Perl code for measuring continuum and equivalent widths ([Riffel & Vale 2011, Ap&SS, 334, 351](https://ui.adsabs.harvard.edu/abs/2011Ap%26SS.334..351R)).
It now also ships with a PyQt5 desktop GUI, if you'd rather point-and-click than write a script.

---

## Installing it

We'd recommend doing this inside an isolated environment (Conda or a plain `venv`) rather than your
system Python — one less thing to worry about later.

### Conda / Mamba

```bash
conda create -n saira_env python=3.12 -y
conda activate saira_env
```

### Or a plain venv

```bash
python3 -m venv saira_env

# Linux / macOS
source saira_env/bin/activate

# Windows
saira_env\Scripts\activate
```

### Then install SAIRA itself

Straight from GitHub:

```bash
pip install git+https://github.com/rriffel/saira.git
```

Or if you want to poke at the code / contribute, clone it and install in editable mode:

```bash
git clone https://github.com/rriffel/saira.git
cd saira
pip install -e .
```

Everything below needs Python 3.10+, plus `astropy`, `pandas`, `scipy`, `matplotlib`, and `PyQt5`
(only needed for the GUI). `pip` pulls all of that in automatically — nothing to install by hand.

---

## The GUI

If you'd rather not write Python, there's a desktop interface for configuring and running SAIRA
interactively.

<p align="center">
  <img src="saira/assets/gui_screenshot.png" alt="SAIRA GUI Main Screen" width="900">
</p>

Launch it any of these ways:

```bash
saira-gui          # console script, after pip install
python -m saira     # same thing, as a module
```

or, from inside Python:

```python
import saira
saira.gui()
```

A quick tour of what's in there:

**Step 1 – Input Files (and redshift).** Point it at a table listing your spectra (with optional
per-spectrum `sigma`/`FWHM`/`R` columns), or just give it a directory and a file extension/pattern and
let it find everything itself. The redshift correction lives here, at the top, because how `z` is
given depends on that choice. It's off by default; once you tick **Enable Redshift Correction**:

- in **Table / File List** mode, each spectrum is corrected with its own redshift, read from the table,
  which then has to be a CSV file whose header contains `file,redshift` (see
  `examples/sdss_table_example.csv`). Run refuses anything else — a missing column, a non-CSV file or a
  spectrum without a valid redshift;
- in **Auto-discover** mode there's no table to hold one `z` per spectrum, so you type a single `z` and
  a warning reminds you that it will be applied to *every* spectrum found in the directory.

**Step 2 – Resolution.** Resolution changes (convolving to a common $\sigma$, FWHM, or $R$) are applied
after the redshift correction, if you turn them on. They're off by default and need their own checkbox
— nothing happens automatically just because your table happens to have a `sigma` column. There's
also a sanity check built in: it won't let you convolve toward a *sharper* resolution than you started
with, and it'll tell you if you've turned resolution changes on without giving it both a starting
point (from the form or from a `sigma`/`FWHM`/`R` column of the table) and a target. Every field has a
**Value / File** selector: pick "File" to give a wavelength-dependent resolution curve, or one initial
resolution per spectrum (see [below](#arrays-files-and-per-spectrum-values) for the formats) — handy in
directory mode, where there's no input table to carry those columns.

**Step 3 – Other Settings.** Set how bad pixels are handled — use a 4th column of the spectra as
pixel flags, mask wavelength regions (rest frame) and choose the maximum bad pixel ratio of an index
(see [Masking bad pixels](#masking-bad-pixels)). Pick how errors get estimated — analytic, either from
[Vollmann & Eversberg (2006)](https://doi.org/10.1002/asna.2006) or by first-order propagation of the
error spectrum, Monte Carlo simulation, or don't bother at all — plus Å-to-magnitude conversion, zeroing out negative EWs, and composite index
formulas. There's also a "Select Indices…" dialog here: it lists every index in your `.ind` file with
a checkbox, and unchecks (with a warning if you try to override it) any whose line limits fall
outside what your spectra actually cover. You don't have to use it, either — clicking Run does the
same range check once for the whole batch and asks you to confirm before skipping anything.

**Step 4 – Plots & Output.** Individual diagnostic plots, a combined multi-panel figure, and where
everything gets saved.

Once a run finishes, the results table has a **Plot…** button that opens a little plotting window —
pick any index (or type an expression like `Mg2 - Fe5270`) for X and Y, tick "Error bars" to overlay
the matching `e_<index>` uncertainties, and save the figure out as PNG/PDF/SVG. You can also load a
second results file and overplot it against the first, handy for comparing runs or checking against
models. The Run Log at the bottom shows everything as it happens — which corrections were applied and
with what values, where every file ended up — and the whole configuration can be saved/loaded as a
`.json` file so you're not re-clicking through the same setup every time.

The same configuration can also be exported as a plain Python script — **Export Script (.py)** writes a
`run_saira.py` that calls `saira()` with exactly the arguments the GUI would use (including a custom
"Select Indices…" choice), so the run can be reproduced on a machine with no display. **Load Script
(.py)** does the reverse: it fills the GUI from such a script, or from one you wrote by hand. It runs the
script's own code with a stand-in `saira()` that only records its arguments (nothing is measured), so
only load scripts you trust; anything the GUI can't represent — e.g. a resolution given as an in-memory
array — is listed in a warning instead of being silently dropped.

---

## Using it as a library

### A table listing your spectra

```python
from saira import saira

result = saira(
    filename='spectra_list.dat',        # ASCII table with a 'file' column
    path_to_files='./spectra/',         # where the spectra actually live
    IndexDefs='Riffel_2019_defs.ind',   # index definitions file
    output_file='measurements.csv'      # always written out as CSV
)
```

### Or just point it at a folder

No list file needed — it'll find everything matching the pattern you give it:

```python
from saira import saira

result = saira(
    path_to_files='./spectra/',
    file_extension='.txt',              # '.txt', '.dat', '*.spec', '*', whatever
    IndexDefs='Riffel_2019_defs.ind',
    output_file='measurements.csv',
    do_resolution=True,                 # this flag has to be on for the two below to matter
    sigma_ini=180.0,                    # assumed starting sigma, km/s
    sigma_fin=250.0                     # convolve everything to this
)
```

`result` comes back as a `pandas.DataFrame` with every measured index and its error, and the same
table gets written to `output_file` as CSV.

One thing worth flagging: `do_resolution` and `do_redshift` both default to `False`, and nothing
happens without them — even `sigma_fin=250.0` above does nothing on its own. Same goes for a table
that already has `sigma`/`FWHM`/`R`/`z` columns: they're ignored unless the matching flag is on. More
on why, and what gets validated, [further down](#a-word-on-resolution-and-redshift).

### Redshift correction works the same way

```python
from saira import saira

result = saira(
    path_to_files='./spectra/',
    file_extension='.txt',
    IndexDefs='Riffel_2019_defs.ind',
    output_file='measurements.csv',
    do_redshift=True,
    z=0.05
)
```

### Dropping indices that fall outside your spectra's range

The GUI's "Select Indices…" check is really just a couple of plain functions underneath, so you can
do the same filtering from a script:

```python
from saira.saira_wapper import (
    list_spectrum_files, get_spectra_wavelength_range, filter_idx_by_range, write_idx_defs,
)
from saira.SairaFunctions import read_idx_defs
from saira import saira

files = list_spectrum_files(path_to_files='./spectra/', file_extension='.txt')
wave_min, wave_max = get_spectra_wavelength_range('./spectra/', files)

idx_definitions = read_idx_defs('Riffel_2019_defs.ind')
in_range = filter_idx_by_range(idx_definitions, wave_min, wave_max)
print(f"{(~in_range).sum()} of {len(idx_definitions)} indices fall outside "
      f"{wave_min:.1f}-{wave_max:.1f} Å and will be skipped.")

# either save the filtered list as a new .ind file for later...
write_idx_defs(idx_definitions, 'defs_in_range.ind', in_range)
result = saira(path_to_files='./spectra/', file_extension='.txt',
                IndexDefs='defs_in_range.ind', output_file='measurements.csv')

# ...or just hand the filtered array straight to saira(), no file needed
result = saira(path_to_files='./spectra/', file_extension='.txt',
                IndexDefs=idx_definitions[in_range], output_file='measurements.csv')
```

---

## From the terminal

None of this needs a notebook — it's all just as happy running from a shell.

### Launching the GUI

```bash
saira-gui
# or
python -m saira
```

### Running a script

Any of the examples above work as a plain `.py` file:

```bash
cat > run_saira.py << 'EOF'
from saira import saira

result = saira(
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

python run_saira.py
```

With `print_log` left unset, everything prints straight to the terminal as it runs — a short summary
of what's turned on, then progress per spectrum:

```
Found 12 spectra matching '*.txt' in './spectra/'
============================================================
SAIRA run configuration
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

### Logging to a file instead

Useful if you're kicking this off with `nohup`, `screen`, or a job scheduler and want to check on it
later rather than watch it live:

```bash
python -c "
from saira import saira
saira(path_to_files='./spectra/', file_extension='.txt',
      IndexDefs='Riffel_2019_defs.ind', output_file='measurements.csv',
      print_log='saira.log')
"
tail -f saira.log
```

---

## Parameters

| Parameter | What it does |
|---|---|
| `filename` | ASCII table listing your spectra, needs a `file` column. Can also carry per-spectrum `sigma`, `FWHM`, `R`, `z` columns. Optional if you're using `file_extension` instead. |
| `path_to_files` | Where the spectra are. Default `'./'`. |
| `file_extension` | Pattern to auto-discover spectra when there's no `filename` (`'.txt'`, `'.dat'`, `'*.spec'`, `'*'`, ...). |
| `IndexDefs` | Path to an `.ind` file, or an already-loaded array (e.g. from `read_idx_defs()`, possibly filtered by `filter_idx_by_range()`). |
| `output_file` | Where the measurements go — always CSV, whatever extension you give it. Default `'demo.txt'`. |
| `do_resolution` | Off by default. Has to be `True` for any resolution correction to apply, table columns included. |
| `sigma_ini` / `sigma_fin` | Starting / target velocity dispersion (km/s). Only matters with `do_resolution=True`. |
| `FWHM_ini` / `FWHM_fin` | Same idea, in FWHM (Å). |
| `R_ini` / `R_fin` | Same idea, as resolving power $R=\lambda/\Delta\lambda$. |
| `do_redshift` | Off by default. Has to be `True` for `z` to apply, table column included. |
| `z` | Redshift to correct for. Only matters with `do_redshift=True`. |
| `simulate` | Number of Monte Carlo iterations, if that's how you want errors estimated. |
| `error` | Analytic errors also for spectra without an error spectrum (noise estimated from the continuum bands). |
| `error_method` | Analytic errors: `'vollmann'` (default, Vollmann & Eversberg 2006) or `'propagation'` (first-order error propagation). |
| `negative_Ew_to_zero` | Clip negative EW measurements to zero. |
| `A_to_mag` | Index names to convert from Å to magnitudes, e.g. `['Mg1', 'Mg2']`. |
| `compute_idx` | Text file of composite index expressions (one per line, e.g. something like `MgFe'`). |
| `print_log` | File to send the log to, instead of stdout. |
| `path_singleind_plots` | Directory for the per-index diagnostic plots. |
| `AllIndicesPlot` | Filename for the combined multi-panel figure. |
| `allindices_plot_path` | Directory for that combined figure. |

---

## A word on resolution and redshift

Both corrections are opt-in, on purpose — set `do_resolution=True` and/or `do_redshift=True` (or tick
the matching box in the GUI) before anything happens. That includes `sigma`/`FWHM`/`R`/`z` columns
already sitting in an input table; they're ignored otherwise.

Resolution can be given in whatever mix of units is convenient — `FWHM_ini` with $\sigma_{\text{fin}}$,
$R_{\text{ini}}$ with $\sigma_{\text{fin}}$, doesn't matter. Internally everything gets converted to
wavelength-dependent FWHM in Å:

- from $\sigma$ (km/s): $\text{FWHM}(\lambda) = (\sigma \cdot 2.355 / c) \cdot \lambda$
- from $R$: $\text{FWHM}(\lambda) = \lambda / R$

### Arrays, files and per-spectrum values

Besides a single number, the resolution parameters and `z` accept:

| What | Accepted by | Format |
|---|---|---|
| Wavelength-dependent curve | `sigma_ini`/`FWHM_ini`/`R_ini` and `sigma_fin`/`FWHM_fin`/`R_fin` | file (or 2-column array) with wavelength (Å) and value; linearly interpolated onto each spectrum and kept constant beyond its ends. A 1-D array with one value per pixel also works. |
| One value per spectrum | `sigma_ini`/`FWHM_ini`/`R_ini` and `z` | list/array with one value per spectrum (same order as the files), or a file with a `file` column and a `sigma`/`FWHM`/`R`/`z` column (otherwise the 2nd column is used) |

The two kinds of file are told apart by their first column: numbers mean a wavelength curve, file
names mean one value per spectrum. Only the first two columns of a curve are read, so the E-MILES
resolution ships as two files: `suport_files/e-miles_spectral_resolution_fwhm.dat` (wavelength, FWHM
in Å; use it for `FWHM_ini`/`FWHM_fin`) and `suport_files/e-miles_spectral_resolution_sigma.dat`
(wavelength, $\sigma$ in km/s; use it for `sigma_ini`/`sigma_fin`). Either can be mixed with a fixed
value on the other side, e.g. `FWHM_ini=<curve>` with `R_fin=1000`. Examples of both kinds of file
ship with the package:

```python
from saira import saira

# E-MILES models: wavelength-dependent FWHM curve (columns: wavelength, FWHM)
models = saira(filename='miles_table.dat', path_to_files='models/', IndexDefs='less_defs.ind',
               do_resolution=True, FWHM_ini='suport_files/e-miles_spectral_resolution_fwhm.dat',
               sigma_fin=300.)

# SDSS spectra found by extension: sigma and z per spectrum (columns: file, sigma, z)
data = saira(path_to_files='sdss_example/', file_extension='.txt', IndexDefs='less_defs.ind',
             do_resolution=True, sigma_ini='examples/sdss_table_example.dat', sigma_fin=300.,
             do_redshift=True, z='examples/sdss_table_example.dat')
```

Columns of the input table (`sigma`, `FWHM`, `R`, `z`) always take precedence over these parameters.
If more than one initial (or target) resolution is given, $\sigma$ wins over $R$, and $R$ over FWHM.
The wavelengths of a curve are those of the spectrum *after* the redshift correction.

A couple of guardrails are built in. Convolution can only broaden a spectrum, never sharpen it, so if
you ask for a target resolution higher than the starting one, you get a clear `ValueError` (or a
dialog, in the GUI) instead of a confusing result. Same if you turn `do_resolution` on but don't
actually give it a starting *and* target value, or turn on `do_redshift` with no `z` anywhere.

Every run also prints a short summary first thing, whether that's to the terminal, a log file, or the
GUI's console — what's active, with what values, and where things are being saved:

```
============================================================
SAIRA run configuration
============================================================
Resolution correction: True
  sigma_ini=180.0  FWHM_ini=None  R_ini=None
  sigma_fin=250.0  FWHM_fin=None  R_fin=None
Redshift correction: False
Output file: measurements.csv (CSV)
============================================================
```

---

## The index definitions file

Pipe-delimited, four columns:

```
# Name     Line                    RedCont                BlueCont                Ref.
Mgb  |  5160.1250-5192.6250  |  5142.6250-5161.3750, 5191.3750-5206.3750  |  (Trager+98)
```

Name, the line's wavelength range (set both limits equal if it's a break index rather than a line),
the continuum bands as comma-separated pairs, and a reference. A couple of ready-made definition files
live in `saira/suport_files/` — `Riffel_2019_defs.ind` and `less_defs.ind`.

If you're mixing indices from different spectral regions (optical + near-IR, say), some will
inevitably fall outside what a given spectrum actually covers. Rather than let those quietly come back
as `NaN`, SAIRA can catch it upfront — see [§Dropping indices that fall outside your spectra's range](#dropping-indices-that-fall-outside-your-spectras-range)
for the scripted version, or the GUI's "Select Indices…" dialog for the point-and-click one.

---

## Masking bad pixels

Bad pixels are handled as in [pyLick](https://pylick.readthedocs.io) (Borghi et al. 2022): they are
replaced by a linear interpolation of the good pixels (the variance is interpolated for the error
spectrum), and an index is returned as `NaN` when the fraction of bad pixels within its bandpasses
(the *bad pixel ratio*) exceeds `bpr_thres`. An index whose central band has no good pixel at all is
never measured. A pixel is flagged as bad when:

- the spectrum file has a **fourth column** and it is non-zero there (`use_flags=True`, the default);
- it falls inside one of the `mask_regions`, a list of `(lambda_min, lambda_max)` intervals in the
  **rest frame**, applied to every spectrum (e.g. emission lines or sky residuals);
- its flux is not finite, or its error is not finite or not positive (unless the whole error
  column is zero or negative, i.e. there is no real error spectrum).

```python
result = saira(filename='spectra.csv', path_to_files='./spectra/', IndexDefs='less_defs.ind',
               do_redshift=True,
               mask_regions=[(4855, 4870), (5570, 5585)],   # e.g. Hbeta emission and a sky line
               bpr_thres=0.3)                               # drop indices with >30% bad pixels
```

At the function level, `eqw()` accepts the same `mask` (boolean array, `True` = bad), `mask_regions`
and `bpr_thres` arguments, and `bad_pixels()` returns the combined mask of a spectrum.

## Errors

Three ways to get them:

1. **Analytic, Vollmann & Eversberg** (`error_method='vollmann'`, the default) — from the S/N of the
   mean flux in the central band and equation (7) of
   [Vollmann & Eversberg (2006)](https://doi.org/10.1002/asna.2006), Astronomische Nachrichten
   ([arXiv version](https://arxiv.org/pdf/astro-ph/0606341.pdf)). Fast, but it ignores the noise of
   the continuum bands and treats the depth of the feature only approximately (on the SDSS examples:
   within ~2% of Monte Carlo on average, with a ~±15% scatter).
2. **Analytic, error propagation** (`error_method='propagation'`) — the error of every pixel is
   propagated, to first order, through exactly the same operations used to measure the index
   (interpolated band edges, mean fluxes of the continuum bands, least-squares pseudo-continuum and
   trapezoidal integration), assuming uncorrelated pixel errors: σ² = Σᵢ (∂I/∂Fᵢ)² σᵢ². It includes
   the noise of the continuum bands and the depth of the feature, and agrees with the Monte Carlo
   estimate to within a few per cent (`index_error()` in `SairaFunctions.py`).

Without an error spectrum (`error=True`), both analytic methods estimate the noise per pixel from the
RMS of a linear fit to the continuum band(s), which is only approximate.

3. **Monte Carlo** (`simulate=N`) — generates `N` synthetic spectra from the flux and error arrays,
   remeasures everything on each one, and takes the standard deviation as the uncertainty.

---

## Convolution

Spectral convolution uses a variable-sigma Gaussian kernel, done in Fourier space following
[Cappellari (2022)](https://ui.adsabs.harvard.edu/abs/2022arXiv220814974C), with error propagation
based on [Klein (2021)](https://ui.adsabs.harvard.edu/abs/2021RNAAS...5...39K). This is what lets
SAIRA handle wavelength-dependent resolution properly instead of assuming a single sigma across the
whole spectrum.

---

## Worked examples

Two notebooks in the repo walk through actual use cases:

- **`Examples.ipynb`** — the full API: measuring indices, convolving to a common resolution,
  converting to magnitudes, composite indices, Monte Carlo errors, diagnostic plots.
- **`Models_and_obs.ipynb`** — measuring indices in SDSS spectra and E-MILES models at a matched
  resolution, then getting ages and metallicities out via grid interpolation.

---

## Citing this

If SAIRA was useful for a paper, please cite the original PACCE paper, on which SAIRA is based:

> Riffel, R. & Vale, T. B., 2011, Ap&SS, 334, 351

---

## License

SAIRA is released under the MIT License — see [LICENSE](LICENSE) for the full text.
