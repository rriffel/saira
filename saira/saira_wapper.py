import os
import sys
import fnmatch
from pathlib import Path
import numpy as np
import pandas as pd

from saira.SairaFunctions import *


def _has_positive(value):
    """True if value is not None and can be interpreted as a number > 0."""
    try:
        return value is not None and float(value) > 0
    except (TypeError, ValueError):
        return False


def _col_has_positive(col):
    """True if a table column has at least one numeric value > 0."""
    try:
        return bool((pd.to_numeric(col, errors='coerce') > 0).any())
    except Exception:
        return False


def _load_idx_definitions(index_defs):
    """Accept either a path to an .ind file or an already-loaded structured array."""
    if isinstance(index_defs, np.ndarray) and index_defs.dtype.names is not None:
        return index_defs
    return read_idx_defs(index_defs)


def list_spectrum_files(filename=None, path_to_files='./', file_extension=None):
    """
    Resolve the list of spectrum file names for a run, using the same logic
    saira() uses internally: a table with a 'file' column if given, otherwise
    directory discovery by extension/pattern.
    """
    if filename is not None and os.path.isfile(filename):
        original_input = pd.read_table(filename)
        return list(original_input['file'])

    ext = file_extension or '.txt'
    if not os.path.isdir(path_to_files):
        raise FileNotFoundError(f"Spectra directory not found: {path_to_files}")

    pattern = ext if ('*' in ext or '?' in ext) else f"*{ext if ext.startswith('.') else '.' + ext}"
    matched_files = sorted([
        f for f in os.listdir(path_to_files)
        if fnmatch.fnmatch(f, pattern) and os.path.isfile(os.path.join(path_to_files, f))
    ])
    return matched_files


def get_spectra_wavelength_range(path_to_files, files):
    """
    Scan a batch of spectrum files and return (global_min, global_max): the
    lowest wavelength found in any spectrum and the highest wavelength found
    in any spectrum (i.e. the union of wavelength coverage across the batch).
    Returns (None, None) if no file could be read.
    """
    mins, maxs = [], []
    for f in files:
        try:
            wave = np.genfromtxt(os.path.join(path_to_files, f), usecols=(0,), unpack=True)
            wave = np.atleast_1d(wave)
            if wave.size:
                mins.append(float(np.nanmin(wave)))
                maxs.append(float(np.nanmax(wave)))
        except Exception:
            continue
    if not mins:
        return None, None
    return min(mins), max(maxs)


def filter_idx_by_range(idx_definitions, wave_min, wave_max):
    """
    Boolean mask (True = keep) for the indices whose Line Limits (the 'defs'
    field) fall entirely within [wave_min, wave_max].
    """
    return np.array([
        (line['defs'][0] >= wave_min) and (line['defs'][1] <= wave_max)
        for line in idx_definitions
    ])


def write_idx_defs(idx_definitions, path, mask=None):
    """Write index definitions (optionally filtered by a boolean mask) to a .ind file."""
    if mask is None:
        mask = np.ones(len(idx_definitions), dtype=bool)
    with open(path, 'w') as f:
        f.write('# ID | Line Limits | continuum | ref\n')
        for line, keep in zip(idx_definitions, mask):
            if not keep:
                continue
            defs_str = '-'.join(f'{v:.4f}' for v in line['defs'])
            conts = line['conts']
            pairs = [f'{conts[i]:.4f}-{conts[i+1]:.4f}' for i in range(0, len(conts), 2)]
            conts_str = ','.join(pairs)
            f.write(f"{line['name']} | {defs_str} | {conts_str} | {line['ref']}\n")


def saira(filename = None,
          path_to_files = './',
          IndexDefs = None,
          output_file = 'demo.txt',
          file_extension = None,
          negative_Ew_to_zero = False,
          path_singleind_plots = None,
          do_resolution = False,
          sigma_ini = None,
          sigma_fin = None,
          FWHM_fin = None,
          FWHM_ini = None,
          R_fin=None,
          R_ini=None,
          do_redshift = False,
          z = None,
          simulate=None,
          error = None,
          A_to_mag = None,
          compute_idx = None,
          print_log = None,
          AllIndicesPlot = None,
          allindices_plot_path = './allIndicesPlots/'
          ):

    '''
     This function computes EW of emission/absorption lines from an input table or directory of spectra.
     It returns the line ID, Equivalent Width, Equivalent Width errors, Flux and line SNR.

     usage: saira(filename='spectra.dat', path_to_files='./spectra/', IndexDefs='defs.ind')
            or
            saira(path_to_files='./spectra/', file_extension='.txt', IndexDefs='defs.ind')

     filename: input ASCII table name with 'file' column (optional if file_extension is used)
     path_to_files: path to directory containing spectra
     file_extension: pattern/extension to scan in path_to_files when filename is None (e.g. '.txt', '.dat', '*.spec')
     IndexDefs: input file with the index definitions
     do_resolution: master flag. If False, sigma/FWHM/R correction is skipped entirely,
                    even if a 'sigma', 'FWHM' or 'R' column is present in the input table.
     do_redshift: master flag. If False, the redshift correction is skipped entirely,
                  even if a 'z' column is present in the input table.
    '''
    if not do_resolution:
        sigma_ini = sigma_fin = FWHM_ini = FWHM_fin = R_ini = R_fin = None
    if not do_redshift:
        z = None

    #changing where you print the info.
    term = sys.stdout
    if print_log is not None:
        log_dir = os.path.dirname(print_log)
        if log_dir and not os.path.isdir(log_dir):
            os.makedirs(log_dir)
        sys.stdout = open(print_log, 'w')

    idx_definitions = _load_idx_definitions(IndexDefs) # loading idx definitions

    # Determine input spectrum files: from table or directory discovery
    if filename is not None and os.path.isfile(filename):
        original_input = pd.read_table(filename)
    else:
        ext = file_extension or '.txt'
        matched_files = list_spectrum_files(filename, path_to_files, file_extension)

        if not matched_files:
            raise FileNotFoundError(
                f"No spectrum files found matching '{ext}' in directory '{path_to_files}'"
            )

        print(f"Found {len(matched_files)} spectra matching '{ext}' in '{path_to_files}'")
        original_input = pd.DataFrame({'file': matched_files})

    file_table =  original_input.copy()
    # check if in the table there is either FWHM (A), sigma (km/s) and R (lambda/d_lambda)
    if do_resolution:
        if 'FWHM' not in file_table:
            file_table['FWHM'] = FWHM_ini
        if 'sigma' not in file_table:
            file_table['sigma'] = sigma_ini
        if 'R' not in file_table:
            file_table['R'] = R_ini
    else:
        file_table['FWHM'] = None
        file_table['sigma'] = None
        file_table['R'] = None

    if do_redshift:
        if 'z' not in file_table:
            file_table['z'] = z
    else:
        file_table['z'] = None

    # ------------------------------------------------------------------
    # Run configuration summary: printed first so it's the first thing
    # visible in the log, whether it goes to a file or to the GUI console.
    # ------------------------------------------------------------------
    print('=' * 60)
    print('SAIRA run configuration')
    print('=' * 60)
    print(f'Resolution correction: {do_resolution}')
    if do_resolution:
        has_ini = (_col_has_positive(file_table['FWHM'])
                   or _col_has_positive(file_table['sigma'])
                   or _col_has_positive(file_table['R']))
        has_fin = _has_positive(FWHM_fin) or _has_positive(sigma_fin) or _has_positive(R_fin)
        if not (has_ini and has_fin):
            raise ValueError(
                "Resolution correction is enabled but incomplete: a value > 0 is required "
                "in at least one of sigma_ini/FWHM_ini/R_ini (as a parameter or a table "
                "column) AND in at least one of sigma_fin/FWHM_fin/R_fin."
            )
        print(f'  sigma_ini={sigma_ini}  FWHM_ini={FWHM_ini}  R_ini={R_ini}')
        print(f'  sigma_fin={sigma_fin}  FWHM_fin={FWHM_fin}  R_fin={R_fin}')

    print(f'Redshift correction: {do_redshift}')
    if do_redshift:
        has_z = ('z' in file_table.columns and file_table['z'].notna().any()) or (z is not None)
        if not has_z:
            raise ValueError(
                "Redshift correction is enabled but no z value was provided "
                "(as a parameter or a table column)."
            )
        print(f'  z={z}')

    print(f'Output file: {output_file} (CSV)')
    if print_log is not None:
        print(f'Log file: {print_log}')
    if path_singleind_plots is not None:
        print(f'Individual index plots directory: {path_singleind_plots}')
    if AllIndicesPlot is not None:
        print(f'All-indices plot directory: {allindices_plot_path}  (filename: {AllIndicesPlot})')
    print('=' * 60)

    # create empty array to add the info from the eqw function
    error_names = np.array(['e_'+name for name in idx_definitions['name']])
    header = np.dstack((idx_definitions['name'], error_names)).flatten()
    header = np.insert(header, 0, 'file')

    data_table = pd.DataFrame(columns = header)
    data_table['file'] = file_table['file'].copy()
    data_table.set_index('file', inplace=True)
    file_table.set_index('file', inplace=True)

    #create folde to add the figures
    if path_singleind_plots is not None:
        if not os.path.exists(path_singleind_plots): os.mkdir(path_singleind_plots)

    #here the code starts to go throu every file, openning them and measuring the indices
    for file in file_table.index:
        print('----------------------------')
        
        #open the files either if they have an error spectrum or not
        try:
            wave, flux, error = np.genfromtxt(os.path.join(path_to_files,file), usecols=(0,1,2), unpack=True)
            print('Doing file '+file+' with error')
        except ValueError:
            wave, flux = np.genfromtxt(os.path.join(path_to_files,file), usecols=(0,1), unpack=True)
            print('Doing file '+file)
        
        path=None #path that lead to the folder for the figures
        if path_singleind_plots is not None:
            path = os.path.join(path_singleind_plots,file)
            print('Individual indices plots saved in '+path)
            if not os.path.isdir(path):
                os.mkdir(path)
        pltallindices=None
        if AllIndicesPlot is not None:
            SP_path = os.path.join(allindices_plot_path,file+'/')
            
            if not os.path.isdir(SP_path):
                path_tmp = Path(SP_path)
                path_tmp.mkdir(parents=True)
            pltallindices = SP_path+AllIndicesPlot
            print('All indices plots saved in  '+pltallindices)

        
        #actual code runs
        head_measurements, measurements = eqw(wave=wave, flux=flux, idx_definitions=idx_definitions,
                                            error=error, simulate=simulate, sigma_fin=sigma_fin,
                                            sigma_ini = file_table.loc[file]['sigma'],
                                            FWHM_fin = FWHM_fin,
                                            FWHM_ini = file_table.loc[file]['FWHM'], R_fin=R_fin,
                                            R_ini=R_ini, z = file_table.loc[file]['z'], path=path,
                                            AllIndicesPlot=pltallindices,
                                            negative_Ew_to_zero=negative_Ew_to_zero
                                            )
       
        data_table.loc[file] = pd.Series(measurements, index=head_measurements)
    
    # cleaning table from columns that are all np.nan
    print('----------------------------')
    data_table = data_table.convert_dtypes()
    float64_cols = list(data_table.select_dtypes(include='Float64'))
    data_table[float64_cols] = data_table[float64_cols].astype(np.float64).values.tolist()
    data_table.dropna(axis=1, how='all', inplace=True)

    #converting given indices to mag
    try:
        for idx in A_to_mag:
            i = np.where(idx_definitions['name'] == idx)[0][0]
            dl = (idx_definitions[i]['defs'][-1]-idx_definitions[i]['defs'][0])
            if 'e_'+idx in data_table:
                data_table['e_'+idx] = (2.5/np.log(10))*(data_table['e_'+idx]/(dl-data_table[idx]))
            data_table[idx] = -2.5*np.log10(1-(data_table[idx]/dl))
            print(idx+' converted to mag')
    except TypeError:
        print('No indices converted to mag')
    
    #computing additional indices
    try:
        with open(compute_idx) as f:
            for line in f:
                data_table.eval(line, inplace=True)
                print('Added index '+line.strip('\n'))
    except:
        print('No additional indices were calculated')

    original_input = original_input.join(data_table, on='file')

    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    original_input.to_csv(output_file, index=False)
    print(f'Measurements saved to {output_file} (CSV)')

    sys.stdout = term
    return original_input
