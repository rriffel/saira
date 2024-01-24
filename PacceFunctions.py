#!/usr/bin/python
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
from scipy import interpolate
from scipy import integrate
import re
import pandas as pd
from astropy import constants

c = constants.c.to('km/s').value

def defs(l):
    '''
    Auxiliar Function to ComputEW. This function reads each line in from input table with the line definitiosn. 
    Usage: defs(l)
    '''
    line=re.sub('\n','',l)
    currentLineLims=[]
    currentContsLims=[]
    lineIDs=[]
    if line[0] != '#':
      line=(re.split('\|',re.sub(' ','',line)))
      lineID=re.sub(' ','',line[0])
      lineIDs.append(lineID)
      linelims=re.split('\-',line[1])
      currentLineLims=np.append(currentLineLims,float(linelims[0]))
      currentLineLims=np.append(currentLineLims,float(linelims[1]))
      clims=re.split('\,',line[2])
      for i in range(0,len(clims)):
          cs=re.split('\-',clims[i])
          for c in cs:
             currentContsLims=np.append(currentContsLims,float(c))
    return lineIDs,currentLineLims,currentContsLims


def GetConts(l_obs,f_obs,linelims,contBandPass):
        # Cutting the parts of the spectrum with the lines and adding the limits.
        line_l=l_obs[(l_obs >= linelims[0]) & (l_obs <=linelims[1])]
        line_f=f_obs[(l_obs >= linelims[0]) & (l_obs <=linelims[1])] 
        FindPointsLine=interpolate.interp1d(l_obs,f_obs)
        first=FindPointsLine(linelims[0])
        last=FindPointsLine(linelims[1])
        line_l=np.append(linelims[0],line_l)
        line_f=np.append(first,line_f)
        line_l=np.append(line_l,linelims[1])
        line_f=np.append(line_f,last)
#      Getting the continuum points.
        cont_l=[]
        cont_f=[]
        ini=0
        fin=1
#       Appending first continuum points (calculating)
        try:
            firstCont=FindPointsLine(contBandPass[ini])
            cont_f=np.append(cont_f, firstCont)
            cont_l=np.append(cont_l, contBandPass[ini])
        except:
            print('1st cointinuum of the line outside the spectrum')
        
        for i in range(0,(int(len(contBandPass)/2))):
            cont_l_tmp=l_obs[(l_obs > contBandPass[ini]) & (l_obs < contBandPass[fin])]
            cont_f_tmp=f_obs[(l_obs > contBandPass[ini]) & (l_obs < contBandPass[fin])]
            cont_l=np.append(cont_l,cont_l_tmp)
            cont_f=np.append(cont_f,cont_f_tmp)
            ini=ini+2
            fin=fin+2
            
#       Appending last continuum point (calculating)
        try:
            lastCont=FindPointsLine(contBandPass[-1])
            cont_f=np.append(cont_f,lastCont)
            cont_l=np.append(cont_l,contBandPass[-1])
        except:
            print('last cointinuum of the line outside the spectrum')
        
        return cont_l,cont_f,line_l,line_f


def computeEW(cont_l,cont_f,line_l,line_f, error=None, ax=None, name_fig=None):
    
    # Fitting the continuum points with a linear fit. 
    (a,b) = np.polyfit(cont_l,cont_f,deg=1)
    cont = lambda x : x*a+b   # Function to use the quadrature integration metodod for the continuum

    ratio = 1 - np.divide(line_f, cont(line_l))

    EW = integrate.trapezoid(ratio, line_l)

    try:
        S=line_f
        N=error
        SN=np.mean(np.divide(S,N))
    except:
        chop = np.diff(cont_l) # get the difference between lambdas
        idx = np.where((chop > 2*(cont_l[3] - cont_l[2])))[0][0]+1 # find where the first continuum finishes 
        #(i found this method to be optimal because taking into considertation all the continuum the spectra 
        #can have variations that are not due to noise and we end up over estimating the errors)
        
        SN=np.mean(cont_f[:idx])/np.std(cont_f[:idx]-cont(cont_l[:idx])) # here i am
        #calculating the signal to noise ratio only in the first defined band 
    
    # error bar estimation based on https://arxiv.org/pdf/astro-ph/0606341.pdf
    #changed their equation (7) to depend only on EQW, d_LAMBDA and the S/N
    
    dl = line_l[-1]-line_l[0]
    eEW = np.sqrt((2*dl-EW)*(dl-EW))/SN
    
    if ax is not None:
            ax.plot(cont_l, cont_f, 'ko', markersize=1)
            ax.plot(line_l, line_f, 'ko', markersize=1)
            ax.plot(np.append(cont_l, line_l), cont(np.append(cont_l, line_l)), 'g-')
            ax.set_xlim(np.min(cont_l)-1, np.max(cont_l)+1)
            ax.set_xlabel(r'$\lambda$')
            ax.set_ylabel(r'Flux')
            fig = ax.get_figure()
            fig.tight_layout()
            fig.savefig(name_fig, format='png')
            plt.close(fig)

    return EW, eEW

def computeBREAK(red_l,red_f,blue_l,blue_f, error=None, ax=None, name_fig=None):
    
    
    F_red = integrate.trapezoid(red_f, red_l)
    F_blue = integrate.trapezoid(blue_f, blue_l)

    ratio = F_red/F_blue
    
    try:
        S=np.append(blue_f, red_f)
        N=error
        SN=np.mean(np.divide(S,N))
    except:
        SN=np.mean(blue_f)/np.std(blue_f) # here i am
        #calculating the signal to noise ratio only in the first defined band 
    
    # error bar estimation based on https://arxiv.org/pdf/astro-ph/0606341.pdf
    #changed their equation (7) to depend only on EQW, d_LAMBDA and the S/N
    
    
    e_ratio = np.sum(np.diff(blue_l)**2)*np.mean(blue_f)/SN
    
    
    if ax is not None:
            ax.plot(blue_l, blue_f, 'ko', markersize=1)
            ax.plot(red_l, red_f, 'ko', markersize=1)
            ax.hlines(F_blue/(blue_l[-1]-blue_l[0]), blue_l[0], blue_l[-1], color='blue')
            ax.hlines(F_red/(red_l[-1]-red_l[0]), red_l[0], red_l[-1], color='red')
            ax.set_xlim(np.min(blue_l)-1, np.max(red_l)+1)
            ax.set_xlabel(r'$\lambda$')
            ax.set_ylabel(r'Flux')
            fig = ax.get_figure()
            fig.tight_layout()
            fig.savefig(name_fig, format='png')
            plt.close(fig)

    return ratio, e_ratio




################################################################################

def varsmooth(x, y, sig_x, xout=None, oversample=1):
    """    
    Fourier convolution with a Gaussian with variable sigma per pixel
    using FFT and analytic Fourier Transform of the Gaussian (like ppxf).
    Convolve a vector or the first dimension (all columns) of an array.
    
    Implements Algorithm 1 in Cappellari+22 (MNRAS submitted)
    https://ui.adsabs.harvard.edu/abs/2022arXiv220814974C

    :param x: coordinate of every pixel in y.
    :param y: input vector or array of colum-spectra.
    :param sig_x: vector with Gaussian sigma of every pixel in units of x.
    :param oversample: oversampling before convolution.
    :param xout: optional output x coordinate used to compute the convolved y.
    :return: convolved vector or columns of the array y.

    """
    # Stretches spectrum to have equal sigma in the new coordinate
    sig = sig_x/np.gradient(x)
    sig_max = np.max(sig)*oversample
    xs = np.cumsum(sig_max/sig)
    n = int(np.ceil(xs[-1] - xs[0]))
    x_new = np.linspace(xs[0], xs[-1], n)
    y_new = interpolate.interp1d(xs, y.T)(x_new)

    # Convolve spectrum with a Gaussian using analytic FT like pPXF
    npad = 2**int(np.ceil(np.log2(n)))
    ft = np.fft.rfft(y_new, npad)
    w = np.linspace(0, np.pi*sig_max, ft.shape[-1])
    ft_gau = np.exp(-0.5*w**2)
    y_conv = np.fft.irfft(ft*ft_gau, npad).T[:n]

    if xout is not None:
        xs = interpolate.interp1d(x, xs)(xout)

    return interpolate.interp1d(x_new, y_conv.T)(xs).T

# Credit: PPXF, Cappellari

def eqw(wave, flux, idx_definitions, error=None, sigma_fin=None, sigma_ini=None, FWHM_fin=None,
        FWHM_ini=None, z=None,path=None):
    
    # Function that gets the spectra, tweeks it in a way given by the user and calls the functions to make the calculation of the EW
    #
    # Parameters:
    #
    # wave: array of the wavlength array of the spectra
    # flux: flux of the spectra you want to calculate the EW
    # idx_definitions: output table from the defs function i.e. fist row: names, second row: wavelength limits for the feature,
    #   third row: wavlength limits for the continuum bands 
    # sigma_fin: velocity dispersion to be used in the convulution with a gaussina kernel
    # FWHM_model: initial velocity dispersion. can be both a number or an array.
    # do_figs: if you want the code to show you the calculations for each line.
    #
    # improvement: the broadening still does not take into account errors. Should it?
    #

    if z is not None:
        wave = wave/(1+z)

    #dwave = np.diff(wave)
    #dwave = np.append(dwave, dwave[-1])
    
    
    try:
        FWHM_ini = (sigma_ini*2.355/c)*wave
    except:
        print('Using FWHM_ini provided', end='\r')
    try:
        FWHM_fin = (sigma_fin*2.355/c)*wave
    except:
        print('Using FWHM_fin provided', end='\r')

    try:
        sigma = np.sqrt(np.power(FWHM_fin,2)-np.power(FWHM_ini,2))/2.355
        sigma = np.nan_to_num(sigma) #turn negative values to zero
        sigma = sigma.clip(0.001) # add a really small number instead os zero (code crashed otherwise)
        flux = varsmooth(x = wave, y = flux, sig_x = sigma)
    except:
        print('Convolution not performed. Check the input parameters you gave for the convolution. \n',
                  sigma_ini, sigma_fin, FWHM_ini, FWHM_fin)
    

    measurements = []
    # maybe there is a better way to not use this if-else for the error
    # but i cannot fugure it out now...   
    if error is not None:
        for line in idx_definitions:
            try:
                (cont_l,cont_f,line_l,line_f)=GetConts(wave,flux,line['defs'],line['conts'])
                (cont_l,err_cont,line_l,err_f)=GetConts(wave,error,line['defs'],line['conts'])
                ax = None
                name_fig = None
                
                if path is not None:
                    fig, ax = plt.subplots()
                    fig.set_size_inches((5, 5))
                    ax.errorbar(wave[(wave >= cont_l[0]) & (wave <=cont_l[-1])],
                                flux[(wave >= cont_l[0]) & (wave <=cont_l[-1])], 
                                yerr = error[(wave >= cont_l[0]) & (wave <=cont_l[-1])],
                                fmt='k-')
                    ax.axvspan(line['conts'][0],line['conts'][1], color='blue', alpha=0.5)
                    ax.axvspan(line['conts'][2],line['conts'][3], color='red', alpha=0.5)
                    vmin = np.min(np.append(cont_f,line_f))
                    vmax = np.max(np.append(cont_f,line_f))
                    ax.set_ylim(vmin-0.1*(vmax-vmin),vmax+0.1*(vmax-vmin))
                    ax.vlines(line['defs'], vmin-0.1*(vmax-vmin), vmax+0.1*(vmax-vmin),
                              linestyle='dashed', color='black')
                    vmin = np.min(np.append(cont_l,line_l))
                    vmax = np.max(np.append(cont_l,line_l))
                    ax.set_xlim(vmin-1,vmax+1)
                    name_fig=path+'/'+line['name']+'.png'

                EW, eEW = computeEW(cont_l,cont_f,line_l,line_f, err_f, ax=ax, name_fig=name_fig)
                measurements.append(EW)
                measurements.append(eEW)
            
            except:
                measurements.append(-99.9)
                measurements.append(-99.9)
    else:
        for line in idx_definitions:
            try:
                (cont_l,cont_f,line_l,line_f)=GetConts(wave,flux,line['defs'],line['conts'])
                ax = None
                name_fig = None
                
                if path is not None:
                    fig, ax = plt.subplots()
                    fig.set_size_inches((5, 5))
                    ax.plot(wave[(wave >= cont_l[0]) & (wave <=cont_l[-1])],
                            flux[(wave >= cont_l[0]) & (wave <=cont_l[-1])], 'k-')
                    ax.axvspan(line['conts'][0],line['conts'][1], color='blue', alpha=0.5)
                    ax.axvspan(line['conts'][2],line['conts'][3], color='red', alpha=0.5)
                    vmin = np.min(np.append(cont_f,line_f))
                    vmax = np.max(np.append(cont_f,line_f))
                    ax.set_ylim(vmin-0.1*(vmax-vmin),vmax+0.1*(vmax-vmin))
                    ax.vlines(line['defs'], vmin-0.1*(vmax-vmin), vmax+0.1*(vmax-vmin),
                              linestyle='dashed', color='black')
                    vmin = np.min(np.append(cont_l,line_l))
                    vmax = np.max(np.append(cont_l,line_l))
                    ax.set_xlim(vmin-1,vmax+1)
                    name_fig=path+'/'+line['name']+'.png'
                
                if line['defs'][0] == line['defs'][1]:
                    (red_l,red_f,blue_l,blue_f) = GetConts(wave,flux,line['conts'][0:2],line['conts'][2:4])
                    EW, eEW = computeBREAK(red_l,red_f,blue_l,blue_f, ax=ax, name_fig=name_fig) 
                else:
                    EW, eEW = computeEW(cont_l,cont_f,line_l,line_f, ax=ax, name_fig=name_fig)
                measurements.append(EW)
                measurements.append(eEW)
            
            except:
                measurements.append(-99.9)
                measurements.append(-99.9)

    return measurements






def pacce(filename,
          IndexDefs,
          output_file = 'demo.txt',
          path_plots = None,
          sigma_ini = None,
          sigma_fin = None,
          FWHM_fin = None,
          FWHM_ini = None,
          z = None,
          A_to_mag = None,
          add_idx = None):
    
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

    # loading idx definitions

    file = np.genfromtxt(IndexDefs, dtype=object, delimiter='|') # loading table
    
    names = np.array([re.findall(r'\S+', t)[0] for t in file[:,0].astype(str)]) # converting the names extracted to the iddices names
    defs = np.array([np.array(re.findall(r'\d+\.\d+', t), dtype='<f8') for t in file[:,1].astype(str)]) # geting the feature definition (always two values)
    conts = [np.array(re.findall(r'\d+\.\d+', t), dtype='<f8') for t in file[:,2].astype(str)]# getting the continuum bands (any even number of values)
    refs = np.array([re.findall(r'\S+', t)[0] for t in file[:,3].astype(str)]) #getting the refs


    idx_definitions = np.empty(len(file), dtype=[('name', names.dtype.str),('defs', defs.dtype.str, (2,)),('conts', 'O'), ('ref', refs.dtype.str)])

    idx_definitions['name'] = names
    idx_definitions['defs'] = defs
    idx_definitions['conts'] = conts
    idx_definitions['ref'] = refs

    # going throught all the files listed in list

    files = np.genfromtxt(filename, dtype=str)

    # create empty array to add the info from the eqw

    error_names = np.array(['e_'+name for name in names])
    header = np.dstack((names, error_names)).flatten()
    header = np.insert(header, 0, 'file')

    data_table = pd.DataFrame(columns = header)
    data_table['file'] = files
    data_table.set_index('file', inplace=True)

    if path_plots is not None:
        if not os.path.exists(path_plots): os.mkdir(path_plots)

    for file in files:
        try:
            wave, flux, error = np.genfromtxt(file, usecols=(0,1,2), unpack=True)
        except:
            wave, flux = np.genfromtxt(file, usecols=(0,1), unpack=True)
            error = None
        
        path=None
        if path_plots is not None:
            path = path_plots+'/indices_'+(file.split('/')[-1])
            os.mkdir(path)
        
        data_table.loc[file] = eqw(wave, flux, idx_definitions, error, sigma_fin,
                                   sigma_ini, FWHM_fin, FWHM_ini, z, path=path)
    
    data_table = data_table.convert_dtypes()
    float64_cols = list(data_table.select_dtypes(include='Float64'))
    data_table[float64_cols] = data_table[float64_cols].astype(np.float64).values.tolist()
    
    try:
        for idx in A_to_mag:
            i = np.where(names == idx)[0][0]
            dl = (idx_definitions[i]['defs'][-1]-idx_definitions[i]['defs'][0])
            data_table['e_'+idx] = (2.5/np.log(10))*(data_table['e_'+idx]/(dl-data_table[idx]))
            data_table[idx] = -2.5*np.log(1-(data_table[idx]/dl))
    except:
        print('No indices converted to mag')
    
    try:
        with open(add_idx) as f:
            for line in f:
                data_table.eval(line, inplace=True)
    except:
        print('No additional indices were calculated')

    
    sourceFile = open(output_file, 'w')
    print(data_table.to_string(), file = sourceFile)
    sourceFile.close()

    return data_table


