##Pacce

PACCE is a code designed to measure indices while handling the most common corrections to
spectra one would want to do uniformily across a data set i.e. broaden to a specific resolution,
correct the spectrum doppler shift, etc. while organizing this info in an easy-to-access tbale 
that can be integrated in python scrtipts. To see the full capabilities of the code, we refer the
user to the Examples.ipynb where all functionalities of the code are displayed.

This allows the same treatment to both data and models, dgrading them both to the same resolution
 facilitating the comparison between them.


Input parameters:

filename: an ascii file containing a list with all the 1-d spectra you want to
    measure the indices. This can have either 2 columns (lambda , flux) or 3 columns (lambda, flux,
    error)
path_to_files: is the path to the directory containing all the data one whats to measure indicated
    in filename.
IndexDefs: path to the ascii file containing all the indiceds you want to measure (reshaping this
    file by adding only the indices within the desired range will improve the efficency of the code)
output_file: path where the code will save a table containing the measured indicies as well as the
    errors

path_plots: if you want the code to plot the spectra and how indices were measured, give it a path
    to store this plots. Beware that this option uses a lot more computational power and disk space!
sigma_ini, sigma_fin, FWHM_fin, FWHM_ini, R_ini, R_fin: _ini correspond to the resolution of the
    spectra being fed to the code whereas _fin correspond to the final resolution you want the 
    indices to be measured in. sigma in km/s, FWHM in A and R is dimentionles (lambda/FWHM). they can
    be mixed also (e.g. sigma_fin=300, FWHM_ini=2.5) 
z: redshift of the spectra.
simulate: the code has an MC routine to simulate the spectra and estimate the errors in out
    measurements. Give the number of iterations you would like to remeasure the indices to e3stimate
    the uncertainties.
A_to_mag: an array where you can name the indices you would like the code convert to mag (e.g. 
    A_to_mag=['Mg2', 'TiO2'])
compute_idx: you can add additional indices that are composite so that the code appends a column with
    this indices(e.g. MgFe', Fe_mean)
print_log: in order to provide the user with what was successful of not during the handling of the
    code, this log prints the changes in the specta, the values it used and so on.(e.g. print_log =
    'print.log')

For future implementations:

- convert into a proper package
- add option to reorder the table in increasing wavelength in the middle of the line.
- implement the possibility of datacubes (extract the spectra, correct for the radial velocity and
    broaden them, measure the indices and save to a table with 'filename_i_j')
- multiprocessing?



