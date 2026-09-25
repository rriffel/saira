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

This is a modernized version of the original SAIRA code ([Riffel & Vale 2011, Ap&SS, 334, 351](https://ui.adsabs.harvard.edu/abs/2011Ap%26SS.334..351R)).
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
# public repo (or via an HTTPS token)
pip install git+https://github.com/rriffel/saira.git@paccegui

# private repo, over SSH
pip install git+ssh://git@github.com/rriffel/saira.git@paccegui
```

Or if you want to poke at the code / contribute, clone it and install in editable mode:

```bash
git clone -b paccegui https://github.com/rriffel/saira.git
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

**Step 1 – Input Files.** Point it at a table listing your spectra (with optional per-spectrum
`sigma`/`FWHM`/`R`/`z` columns), or just give it a directory and a file extension/pattern and let it
find everything itself.

**Step 2 – Redshift & Resolution.** Redshift correction is applied first if you turn it on, then
resolution changes (convolving to a common $\sigma$, FWHM, or $R$) if you turn *that* on too. Both are
off by default and need their own checkbox — nothing happens automatically just because your table
happens to have a `z` or `sigma` column. There's also a sanity check built in: it won't let you
convolve toward a *sharper* resolution than you started with, and it'll tell you if you've turned
resolution changes on without giving it both a starting point and a target.

**Step 3 – Other Settings.** Pick how errors get estimated — the analytic equation from
[Vollmann & Eversberg (2006)](https://doi.org/10.1002/asna.2006), Monte Carlo simulation, or don't
bother at all — plus Å-to-magnitude conversion, zeroing out negative EWs, and composite index
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
| `error` | Use the equation-based (Vollmann & Eversberg) error estimate instead. |
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

## Errors

Two ways to get them:

1. **Equation** (the default, when there's an error spectrum to work with) — estimated from the S/N
   in the line and continuum, using the formalism in [Vollmann & Eversberg (2006)](https://doi.org/10.1002/asna.2006),
   Astronomische Nachrichten, DOI 10.1002/asna.2006 ([arXiv version](https://arxiv.org/pdf/astro-ph/0606341.pdf)).
2. **Monte Carlo** (`simulate=N`) — generates `N` synthetic spectra from the flux and error arrays,
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

If SAIRA was useful for a paper, please cite:

> Riffel, R. & Vale, T. B., 2011, Ap&SS, 334, 351

---

## License

Open source — see the repository for the license terms.
