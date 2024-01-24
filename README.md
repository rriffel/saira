PACCE is a code designed to measure indices while handling the most common corrections to
spectra one would want to do uniformily across a data set i.e. broaden to a specific resolution,
correct the spectrum doppler shift, etc. while organizing this info in an easy'to'access tbale 
that can be integrated in python scrtipts.


Input parameters:

filename: an ascii file containing a list with the paths to all the 1-d spectra you want to
    measure the indices.
IndexDefs: path to the ascii file containing all the indiceds you want to measure (reshaping this
    file by adding only the indices within the desired range will improve the efficency of the code)
output: path where the code will save a table containing the measured indicies as well as the errors
sigma_ini, sigma_fin, FWHM_fin, FWHM_ini: _ini correspond to the resolution of the spectra being
    whereas _fin correspond to the final resolution you want the indices to be measured in.
    sigma in km/s and FWHM in A. they can be mixed also (e.g. sigma_fin=300, FWHM_ini=2.5) 
z: redshift of the spectra. this needs to be improved to be passed along with the file list.

For future implementations (by order of priority):
 
- get the file list and have all the info the user would like to have in the final table (e.g. age,
    metalicity...) and just append the columns adding the Indices. Use this to have a column with
    FWHM/sigma and z to be used later.
- read from both txt and fits

- add option to 'clean' the table when all the indices are null i.e. when the spectral range does not
    reach that definition.
- add option to reorder the table in increasing wavelength in the middle of the line.
- implement the possibility of datacubes (extract the spectra, correct for the radial velocity and
    broaden them, measure the indices and save to a table with 'filename_i_j')
- add MC option to estimate errors



