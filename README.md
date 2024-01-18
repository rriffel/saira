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
    whereas _fin correspond to the final resolution you want the indices to be measured in
z

For future implementations (by order of priority):
 

- add warning for bad lines (e.g. if part of the continuum is missing) like a '!' in front of the
    measurement, but still add the info in the table and give the user the otion to remove the ! by
    doing smth like (data['result'] = data['result'].map(lambda x: x.lstrip('!'))). 
- add a ploting option.

- get the file list and have all the info the user would like to have in the final table (e.g. age,
    metalicity...) and just append the columns adding the Indices. Use this to have a column with
    FWHM/sigma and z to be used later.
- add option to convert given indices to mag (e.g. A_to_mag=['Mg2'])
- add option to have an additional file where one can add indices that are combination of other ones
    (e.g. MgFe_prime)
- allow the calculation of breaks (e.g. Dn4000)
- read from both txt and fits

- add option to 'clean' the table when all the indices are null i.e. when the spectral range does not
    reach that definition.
- add option to reorder the table in increasing wavelength in the middle of the line.
- implement the possibility of datacubes (extract the spectra, correct for the radial velocity and
    broaden them, measure the indices and save to a table with 'filename_i_j')



