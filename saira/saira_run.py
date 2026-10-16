from saira.saira_wapper import saira


a = saira(filename='./galaxies.dat', path_to_files='./',
         IndexDefs='./finalIndexDef.ind',
         output_file='EWMeasurements_neg_to_zero.dat',error=True,negative_Ew_tozero=True,
         path_singleind_plots='./Saira_Figures/',allindices_plot_path='./Saira_Figures/', AllIndicesPlot='All_indices_plot.png')
