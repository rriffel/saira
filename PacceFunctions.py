#!/usr/bin/python
import os, glob
from pylab import *
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.mlab as mlab
from scipy import interpolate
from scipy import integrate
from scipy import ndimage
import re
import time
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
        firstCont=FindPointsLine(contBandPass[0])
        cont_f=np.append(firstCont,cont_f)
        cont_l=np.append(contBandPass[0],cont_l)
        for i in range(0,(int(len(contBandPass)/2))):
             cont_l_tmp=l_obs[(l_obs > contBandPass[ini]) & (l_obs < contBandPass[fin])]
             cont_f_tmp=f_obs[(l_obs > contBandPass[ini]) & (l_obs < contBandPass[fin])]
             cont_l=np.append(cont_l,cont_l_tmp)
             cont_f=np.append(cont_f,cont_f_tmp)
             ini=fin+1
             fin=ini+1
#       Appending last continuum points (calculating)
        lastCont=FindPointsLine(contBandPass[-1])
        cont_f=np.append(cont_f,lastCont)
        cont_l=np.append(cont_l,contBandPass[-1])
        return cont_l,cont_f,line_l,line_f


def computeEW(cont_l,cont_f,line_l,line_f, error=None):
    
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
    #print(cont_f)

    return EW, eEW



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

def eqw(wave, flux, idx_definitions, error=None, sigma_fin=None, sigma_ini=None, FWHM_fin=None, FWHM_ini=None, z=None):#, name, do_figs=False):
    
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
    

    eqw_measurements = []
    # maybe there is a better way to not use this if-else for the error
    # but i cannot fugure it out now...   
    if error is not None:
        for line in idx_definitions:
            try:
                (cont_l,cont_f,line_l,line_f)=GetConts(wave,flux,line['defs'],line['conts'])
                (cont_l,err_cont,line_l,err_f)=GetConts(wave,error,line['defs'],line['conts'])
                
                EW, eEW = computeEW(cont_l,cont_f,line_l,line_f, err_f)
                eqw_measurements.append(EW)
                eqw_measurements.append(eEW)
            
            except:
                eqw_measurements.append(-99.9)
                eqw_measurements.append(-99.9)
    else:
        for line in idx_definitions:
            try:
                (cont_l,cont_f,line_l,line_f)=GetConts(wave,flux,line['defs'],line['conts'])
                EW, eEW = computeEW(cont_l,cont_f,line_l,line_f)
                eqw_measurements.append(EW)
                eqw_measurements.append(eEW)
            
            except:
                eqw_measurements.append(-99.9)
                eqw_measurements.append(-99.9)

    return eqw_measurements






def pacce(filename, IndexDefs, Doplots = False, output_file = 'demo.txt', sigma_ini = None,
          sigma_fin = None, FWHM_fin = None, FWHM_ini = None, z=None):
    
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
    conts = np.array([np.array(re.findall(r'\d+\.\d+', t), dtype='<f8') for t in file[:,2].astype(str)], dtype='object')# getting the continuum bands (any even number of values)

    idx_definitions = np.empty(len(file), dtype=[('name', names.dtype.str),('defs', defs.dtype.str, (2,)),('conts', conts.dtype.str)])

    idx_definitions['name'] = names
    idx_definitions['defs'] = defs
    idx_definitions['conts'] = conts

    # going throught all the files listed in list

    files = np.genfromtxt(filename, dtype=str)

    # create empty array to add the info from the eqw

    error_names = np.array(['e_'+name for name in names])
    header = np.dstack((names, error_names)).flatten()
    header = np.insert(header, 0, 'file')

    data_table = pd.DataFrame(columns = header)
    data_table['file'] = files
    data_table.set_index('file', inplace=True)

    for file in files:
        try:
            wave, flux, error = np.genfromtxt(file, usecols=(0,1,2), unpack=True)
        except:
            wave, flux = np.genfromtxt(file, usecols=(0,1), unpack=True)
            error = None
        
        data_table.loc[file] = eqw(wave, flux, idx_definitions, error, sigma_fin,
                                   sigma_ini, FWHM_fin, FWHM_ini, z)
    
    sourceFile = open(output_file, 'w')
    print(data_table.to_string(), file = sourceFile)
    sourceFile.close()

    return data_table


'''  
    graph=0
    fignumber=0
    Computations_EW=[]
    Computations_eEW=[]
    Computations_SN=[]
    Computations_Flux=[]
    LIDs=[]
    for line in defsfile:
        line=re.sub('\n','',line)
        line=re.sub(' ','',line)
        if line[0] != '#':
            # Getting the lines and continuum band passes from the input file.
            # arrumar para ter o espectro de erro no simulate tambem.
            (lineID,linelims,contBandPass)=defs(line)
            try:
                if simulate:
                    EW_temp=[]
                    (cont_l,cont_f,line_l,line_f)=GetConts(l_obs,f_obs,linelims,contBandPass)
                    SN=np.mean(cont_f)/np.std(cont_f)
                    FindPointsLine=interpolate.interp1d(l_obs,f_obs)
                    (a_sim,b_sim)=np.polyfit(cont_l,cont_f,deg=1)
                    ajustCont=a_sim*cont_l +b_sim
                    sigma=sqrt((ajustCont-cont_f)**2)
                    for i in range(0,SimTimes):                                      
                        simCont=np.random.normal(cont_f,sigma)
                    # Fitting the continuum points with a linear fit. 
                        (a,b)=np.polyfit(cont_l,simCont,deg=1)
                        aj=lambda x : x*a+b   # Function to use the quadrature integration metodod for the continuum
                        FCont=integrate.quad(aj,linelims[0],linelims[1])[0]
                        FLine=integrate.quad(FindPointsLine,linelims[0],linelims[1],epsrel=1E-2)[0]
                        EWsim=(1.0-(FLine/FCont))*(linelims[1]-linelims[0])
                        Flux=(FCont-FLine)
                        EW_temp=np.append(EW_temp,EWsim)
                    EW=np.mean(EW_temp)
                    eEW=np.std(EW_temp)
    #                    else:
    #                           EW=-999
    #                           eEW=-999

                if not simulate:
                 
                    (cont_l,cont_f,line_l,line_f)=GetConts(l_obs,f_obs,linelims,contBandPass)
                    FindPointsLine=interpolate.interp1d(l_obs,f_obs)
                    # Fitting the continuum points with a linear fit. 
                    (a,b)=np.polyfit(cont_l,cont_f,deg=1)
                    aj=lambda x : x*a+b   # Function to use the quadrature integration metodod for the continuum
                    FCont=integrate.quad(aj,linelims[0],linelims[1])[0]
                    FLine=integrate.quad(FindPointsLine,linelims[0],linelims[1],epsrel=1E-2)[0]
                    EW=(1.0-(FLine/FCont))*(linelims[1]-linelims[0])
                    Flux=(FCont-FLine)
                    if error:
                        FindPoints=interpolate.interp1d(l_obs,f_obs)
                        S=FindPoints(cont_l)
                        FindPoints=interpolate.interp1d(l_obs,ef_obs)
                        N=FindPoints(cont_l)
                        SN=np.mean(S/N)
                    if not error:
                        SN=np.mean(cont_f)/np.std(cont_f)
                    eEW=np.sqrt(1.0+(FCont/FLine)) *(((linelims[1]-linelims[0]) - EW)/SN) #https://arxiv.org/pdf/astro-ph/0606341.pdf
                    EW=EW
                    eEW=eEW
    #                    else:
    #                       EW=-999.
    #                       eEW=-999.
            except:
                    EW=-999.
                    eEW=-999.
                    SN=-999.
                    Flux=-999.
                    print(galname, "<File not found or problems in the file>")
                
#            print lineID[0], EW, eEW, SN
            LIDs.append(lineID[0])
            Computations_EW=np.append(Computations_EW,EW)
            Computations_eEW=np.append(Computations_eEW,eEW)
            Computations_SN=np.append(Computations_SN,SN)
            Computations_Flux=np.append(Computations_Flux,Flux)

    ###################################################################################
    #                                                                                 #
    #                                                                                 #
    #                                      Plots                                      #
    #                                                                                 #
    #                                                                                 #
    ###################################################################################
            if Doplots:
                    if (os.path.exists('Pacce_Figures')==False): 
                        os.mkdir('Pacce_Figures')

                    mpl.rcParams['axes.labelsize']= 10
                    mpl.rcParams['legend.fontsize']= 10
                    mpl.rcParams['xtick.major.size']= 8
                    mpl.rcParams['xtick.minor.size']= 4
                    mpl.rcParams['ytick.major.size']= 8
                    mpl.rcParams['ytick.minor.size']= 4
                    mpl.rcParams['xtick.labelsize']=10
                    mpl.rcParams['ytick.labelsize']= 10
                    if (graph <= 6):
                        if graph ==0:
                            fig=plt.figure(figsize=(7.9,8.5))
                        graph=graph+1
                        ax=plt.subplot(3,2,graph)
                        plt.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=0.6)
                        # Observed spectrum
                        l_obsLine=l_obs[(l_obs >= contBandPass[0]) & (l_obs <=contBandPass[-1])]
                        f_obsLine=f_obs[(l_obs >= contBandPass[0]) & (l_obs <=contBandPass[-1])]
                        plt.plot(l_obsLine,f_obsLine,color='blue') #,label='Spectrum')
                        # line and line limits
                        ax.plot(line_l,line_f,color='red', label=str(lineID[0]))
                        ax.axvline(linelims[0],0,1,color='red',ls='--')
                        ax.axvline(linelims[1],0,1,color='red',ls='--')#,label='limits')
                        setp(ax.get_xticklabels(), visible=True, rotation=60)
                        # Continuum points
                        ax.plot(cont_l,cont_f,'ro')#,label='Cont. Points')
                        cont_ajust=np.arange(cont_l[0],cont_l[-1],0.01)
                        ajust=cont_ajust*a + b
                        ax.plot(cont_ajust,ajust,color='black',ls=':', label='Cont.') #label='Cont '+str(lineID[0])
                        ax.set_xlabel('$\lambda$')
                        ax.legend(frameon=False,prop={'size':8})
                        #text(0.5, 0.5,str(FLine/FCont), horizontalalignment='center',verticalalignment='center',transform=ax.transAxes,color='red')
                        if EW == -999:
                            text(0.5, 0.5,'NOT USED', horizontalalignment='center',verticalalignment='center',transform=ax.transAxes,color='red')
                    if graph == 6:
                        outname=os.path.splitext(galname)[0]
                        #print outname 
                        title=outname
                        fig.suptitle(title, fontsize=16)
                        savefig('./Pacce_Figures/'+outname+'_'+str(fignumber)+'.png')
                        fignumber=fignumber+1
                        graph=0
                        clf()
                       # try:
                       #    ax.close()
                       # except:
                       #    fig.delaxes(ax)
                    else:
                       outname=os.path.splitext(galname)[0]
                       
                       title=outname
                       fig.suptitle(title, fontsize=16)
                       savefig('./Pacce_Figures/'+outname+'_'+str(fignumber)+'.png')
                
    Computations=np.column_stack((Computations_EW,Computations_eEW,Computations_Flux,Computations_SN))
    return LIDs, Computations

'''