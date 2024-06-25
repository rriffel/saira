from pacce.pacce_wapper import pacce

#a = pacce(filename='./test_table.dat', path_to_files='./test_spectra/',
#         IndexDefs='./suport_files/Elham_pacce_Defs.ind',
#         output_file='indicies_MILES_tmp.txt', print_log='file.txt')


#a = pacce(filename='./galaxies.dat', path_to_files='./',
#         IndexDefs='./finalIndexDef.ind',
#         output_file='EWMeasurements_neg_to_zero.dat',error=True,negative_Ew_to_zero=True)


a = pacce(filename='./galaxies.dat', path_to_files='./',
         IndexDefs='./finalIndexDef.ind',
         output_file='EWMeasurements_neg_to_zero.dat',error=True,negative_Ew_tozero=True,
         path_singleind_plots='./Pacce_Figures/',allindices_plot_path='./Pacce_Figures/', AllIndicesPlot='All_indices_plot.png')
