import os
import numpy as np
import pandas as pd
import sys
from pathlib import Path

from PacceFunctions import *

def pacce(filename,
          path_to_files,
          IndexDefs,
          output_file = 'demo.txt',
          negative_Ew_to_zero = False,
          path_singleind_plots = None,
          sigma_ini = None,
          sigma_fin = None,
          FWHM_fin = None,
          FWHM_ini = None,
          R_fin=None,
          R_ini=None,
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
     This function computs EW of emission/absorption lines from an input file and an input spectrum. 
     It returns the line ID, Equivalent Width, Equivalent Width errors, Flux and line SNR.
     
     
     usage: ComputEW(galname,IndexDefs,Doplots=True/False,simulate=False,SimTimes=100,treshold=0.)
     galname: input ASCII file name
     IndexDefs: input file with the indexes definitions
     Doplots: True or False
     simulate: True or False
     SimTimes: integer with the number of simulations
     treshold: fraction of the line continuum compared with the bandpass.
    
    '''
    #changing where you print the info. 
    term = sys.stdout
    if print_log is not None:
        sys.stdout = open(print_log, 'w')


    idx_definitions = read_idx_defs(IndexDefs) # loading idx definitions

    original_input = pd.read_table(filename) # going throught all the files listed in list
    
    file_table =  original_input.copy()
    # check if in the table there is either FWHM (A), sigma (km/s) and R (lambda/d_lambda)
    if 'FWHM' not in file_table:
        print('FWHM not found in table')
        file_table['FWHM'] = FWHM_ini
    else:
        print('FWHM found in table')
    if 'sigma' not in file_table:
        print('sigma not found in table')
        file_table['sigma'] = sigma_ini
    else:
        print('sigma found in table')
    if 'R' not in file_table:
        print('R not found in table')
        file_table['R'] = R_ini    
    else:
        print('R found in table')
    if 'z' not in file_table:
        print('z not found in table')
        file_table['z'] = z
    else:
        print('z found in table')
    
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

    sourceFile = open(output_file, 'w')
    print(original_input.to_string(index=False), file = sourceFile)
    sourceFile.close()

    sys.stdout = term
    return original_input
