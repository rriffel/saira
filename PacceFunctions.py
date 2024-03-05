import numpy as np
import matplotlib.pyplot as plt
from scipy import interpolate
from scipy import integrate
import re
from astropy import constants

c = constants.c.to('km/s').value

def read_idx_defs(ref_table):
    '''
    Function designed to read the table containing the definitions of the indices to be used by the rest of the code.

    Parameters:
    
    ref_table: ascii file with the information regarding the indices.
    
    '''
    file = np.genfromtxt(ref_table, dtype=object, delimiter='|') # loading table
    
    names = np.array([re.findall(r'\S+', t)[0] for t in file[:,0].astype(str)]) # converting the names extracted to the iddices names
    defs = np.array([np.array(re.findall(r'\d+\.\d+', t), dtype='<f8') for t in file[:,1].astype(str)]) # geting the feature definition (always two values)
    conts = [np.array(re.findall(r'\d+\.\d+', t), dtype='<f8') for t in file[:,2].astype(str)]# getting the continuum bands (any even number of values)
    refs = np.array([re.findall(r'\S+', t)[0] for t in file[:,3].astype(str)]) #getting the refs


    idx_definitions = np.empty(len(file), dtype=[('name', names.dtype.str),('defs', defs.dtype.str, (2,)),('conts', 'O'), ('ref', refs.dtype.str)])

    idx_definitions['name'] = names
    idx_definitions['defs'] = defs
    idx_definitions['conts'] = conts
    idx_definitions['ref'] = refs

    return idx_definitions



def GetConts(l_obs,f_obs,linelims,contBandPass):
        '''
        Function to cut a spectrum given a line definition.

        Parameters:
        l_obs: wavelength array for the oservations
        f_obs: flux array with the spectrum
        linelims: array with the begining and end of the line definition
        contBandPass: array that accepts only even numbers >= 4 and takes them pair-wise to define the continuum
            i.e. contBandPass[0],contBandPass[1] are the limits for the first band pass
        
        '''
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
        for i in range(0,(int(len(contBandPass)/2))):
            cont_l_tmp = []
            cont_f_tmp = []
            #Appending first continuum points (calculating)
            
            try:
                firstCont=FindPointsLine(contBandPass[ini])
                cont_f_tmp=np.append(cont_f_tmp, firstCont)
                cont_l_tmp=np.append(cont_l_tmp, contBandPass[ini])
            except:
                pass #print('1st cointinuum of the line outside the spectrum')
            
            cont_l_tmp=np.append(cont_l_tmp, l_obs[(l_obs > contBandPass[ini]) & (l_obs < contBandPass[fin])])
            cont_f_tmp=np.append(cont_f_tmp, f_obs[(l_obs > contBandPass[ini]) & (l_obs < contBandPass[fin])])
            
            #Appending last continuum point (calculating)
            try:
                lastCont=FindPointsLine(contBandPass[fin])
                cont_f_tmp=np.append(cont_f_tmp,lastCont)
                cont_l_tmp=np.append(cont_l_tmp,contBandPass[fin])
            except:
                pass #print('last cointinuum of the line outside the spectrum')
            
            cont_f = np.append(cont_f, integrate.trapezoid(cont_f_tmp, cont_l_tmp)/(cont_l_tmp[-1]-cont_l_tmp[0]))
            cont_l = np.append(cont_l,(cont_l_tmp[-1]+cont_l_tmp[0])/2.0)
            ini=ini+2
            fin=fin+2
        #print(cont_l,cont_f,line_l,line_f)
        return cont_l,cont_f,line_l,line_f


def computeEW(cont_l,cont_f,line_l,line_f):
    
    # Fitting the continuum points with a linear fit. 
    (a,b) = np.polyfit(cont_l,cont_f,deg=1)
    cont = lambda x : x*a+b   # Function to use the quadrature integration metodod for the continuum

    ratio = 1 - np.divide(line_f, cont(line_l))

    EW = integrate.trapezoid(ratio, line_l)

    return EW

def computeBREAK(red_l,red_f,blue_l,blue_f, ax=None, name_fig=None):
    
    ratio = red_f/blue_f

    return ratio




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

################################################################################

def varsmooth_error(x, error, sig_x, xout=None, oversample=1):
    """
    This is a trial to change varsmooth algorithm to be able to propagate the 
    uncertaities in the spectrum, based on the calculations done by Randolf Klein
    https://ui.adsabs.harvard.edu/abs/2021RNAAS...5...39K/abstract
    
    Fourier convolution with a Gaussian with variable sigma per pixel
    using FFT and analytic Fourier Transform of the Gaussian (like ppxf).
    Convolve a vector or the first dimension (all columns) of an array.
    
    Implements Algorithm 1 in Cappellari+22 (MNRAS submitted)
    https://ui.adsabs.harvard.edu/abs/2022arXiv220814974C

    :param x: coordinate of every pixel in y.
    :param error: input vector or array of colum-spectra.
    :param sig_x: vector with Gaussian sigma of every pixel in units of x.
    :param oversample: oversampling before convolution.
    :param xout: optional output x coordinate used to compute the convolved y.
    :return: convolved vector or columns of the array y.

    """
    y = error**2 #one needs to convolve the vatriance not the error
    sig_x = sig_x/np.sqrt(2) #one needs to convolve with the square of the
    #kernel of the convolution. in hte case of a gaussian kernel, that is
    #a gaussian with sigma/sqrt(2).

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

    return np.sqrt(interpolate.interp1d(x_new, y_conv.T)(xs).T)


# Credit: PPXF, Cappellari

def eqw(wave, 
        flux,
        idx_definitions,
        error=None,
        simulate = None,
        sigma_fin=None,
        sigma_ini=None,
        FWHM_fin=None,
        FWHM_ini=None,
        R_fin=None,
        R_ini=None,
        z=None,
        path=None):
    
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
    # 
    #

    #check if the code is getting already the output from read_idx_defs of if its the file definition.

    try:
        tmp = idx_definitions.dtype
    except AttributeError:
        idx_definitions = read_idx_defs(idx_definitions)

    #redshift correction
    if z is not None:
        wave = wave/(1+z)
    
    #checking for a file with the sigma/FWHM info
    try:
        sigma_ini = np.genfromtxt(sigma_ini)
        sigma_ini = sigma_ini[:,1]
    except:
        try:
            FWHM_ini = np.genfromtxt(FWHM_ini)
            FWHM_ini = FWHM_ini[:,1]
        except:
            try:
               R_ini = np.genfromtxt(R_ini) 
               R_ini = R_ini[:,1]
            except:
                pass

            
    
    #converting sigma or R to FWHM
    try:
        FWHM_ini = (sigma_ini*2.355/c)*wave
    except:
        try:
            FWHM_ini = np.divide(wave,R_ini)
        except:
            pass #print('Using FWHM_ini provided', end='\r')
    try:
        FWHM_fin = (sigma_fin*2.355/c)*wave
    except:
        try:
            FWHM_fin = np.divide(wave,R_fin)
        except:
            pass #print('Using FWHM_fin provided', end='\r')

    measurements = []
    head_measurements = []
    # maybe there is a better way to not use this if-else for the error
    # but i cannot fugure it out now...   
    if error is not None:
        try:
            sigma = np.sqrt(np.power(FWHM_fin,2)-np.power(FWHM_ini,2))/2.355
            sigma = np.nan_to_num(sigma) #turn negative values to zero
            sigma = sigma.clip(0.01) # add a really small number instead of zero (code crashed otherwise)
            flux_new = varsmooth(x = wave, y = flux, sig_x = sigma)
            error_new = varsmooth_error(x = wave, error=error, sig_x = sigma) #one needs to convolve the variance with the square of the kernel
            print('Convolution successfull from', FWHM_ini, 'to', FWHM_fin)
            flux = flux_new
            error = error_new
        except:
            print('Convolution not performed. Check FWHM ini and fin: ',FWHM_ini, FWHM_fin)
        
        if simulate is not None:
            error[np.where(error <= 0)] = 1e-20
            sim_flux=np.random.normal(flux,error, size=(simulate, len(flux)))
            print(simulate,'spectra were created')
        
        for line in idx_definitions:
            try:
                (cont_l,cont_f,line_l,line_f)=GetConts(wave,flux,line['defs'],line['conts'])
                ax = None
                name_fig = None
                
                if path is not None:
                    fig, ax = plt.subplots()
                    fig.set_size_inches((5, 5))
                    ax.errorbar(wave[(wave >= np.min(line['conts'])) & (wave <=np.max(line['conts']))],
                                flux[(wave >= np.min(line['conts'])) & (wave <=np.max(line['conts']))], 
                                yerr = error[(wave >= np.min(line['conts'])) & (wave <=np.max(line['conts']))],
                                fmt='k-')
                    ax.axvspan(line['conts'][0],line['conts'][1], color='blue', alpha=0.5)
                    ax.axvspan(line['conts'][2],line['conts'][3], color='red', alpha=0.5)
                    vmin = np.min(flux[(wave >= np.min(line['conts'])) & (wave <=np.max(line['conts']))])
                    vmax = np.max(flux[(wave >= np.min(line['conts'])) & (wave <=np.max(line['conts']))])
                    ax.set_ylim(vmin-0.1*(vmax-vmin),vmax+0.1*(vmax-vmin))
                    ax.vlines(line['defs'], vmin-0.1*(vmax-vmin), vmax+0.1*(vmax-vmin),
                              linestyle='dashed', color='black')
                    name_fig=path+'/'+line['name']+'.png'
                    if line['defs'][0] == line['defs'][1]:
                        ax.hlines(cont_f[0], line['conts'][0], line['conts'][1], color='blue')
                        ax.hlines(cont_f[1], line['conts'][2], line['conts'][3], color='red')
                    else:
                        (a,b) = np.polyfit(cont_l,cont_f,deg=1)
                        cont = lambda x : x*a+b 
                        ax.plot(cont_l, cont_f, 'ko', markersize=1)
                        ax.plot(line_l, line_f, 'ko', markersize=1)
                        ax.plot(cont_l, cont(cont_l), 'g-')
                    ax.set_xlim(np.min(line['conts'])-1, np.max(line['conts'])+1)
                    ax.set_xlabel(r'$\lambda$')
                    ax.set_ylabel(r'Flux')
                    fig.tight_layout()
                    fig.savefig(name_fig, format='png')
                    plt.close(fig)

                if line['defs'][0] == line['defs'][1]:
                    EW = computeBREAK(red_l=cont_l[1],red_f=cont_f[1],blue_l=cont_l[0],blue_f=cont_f[0]) 
                    if simulate is not None:
                        eEW=[]
                        for i in range(simulate):
                            (cont_l,cont_f,line_l,line_f)=GetConts(wave,sim_flux[i,:],line['defs'],line['conts'])
                            eEW.append(computeBREAK(red_l=cont_l[1],red_f=cont_f[1],blue_l=cont_l[0],blue_f=cont_f[0]))
                        eEW = np.std(eEW)
                    else:
                        (cont_l,err_cont,line_l,err_f)=GetConts(wave,error,line['defs'],line['conts'])
                        eEW = EW * np.sqrt((err_f[0]/cont_f[0])**2+(err_f[1]/cont_f[1])**2) #this may need to change to account for the covariance
                else:
                    EW = computeEW(cont_l,cont_f,line_l,line_f)
                    if simulate is not None:
                        eEW=[]
                        for i in range(simulate):
                            (cont_l,cont_f,line_l,line_f)=GetConts(wave,sim_flux[i,:],line['defs'],line['conts'])
                            eEW.append(computeEW(cont_l,cont_f,line_l,line_f))
                        eEW = np.std(eEW)
                    else:
                        (cont_l,err_cont,line_l,err_f)=GetConts(wave,error,line['defs'],line['conts'])
                        S=line_f
                        N=err_f
                        SN=np.mean(np.divide(S,N))
                        dl = line_l[-1]-line_l[0]
                        eEW = np.sqrt((2*dl-EW)*(dl-EW))/SN
                        # error bar estimation based on https://arxiv.org/pdf/astro-ph/0606341.pdf
                        #changed their equation (7) to depend only on EQW, d_LAMBDA and the S/N
                
                
                measurements.append(EW)
                head_measurements.append(line['name'])
                measurements.append(eEW)
                head_measurements.append('e_'+line['name'])
            except:
                measurements.append(np.nan)
                head_measurements.append(line['name'])
                measurements.append(np.nan)
                head_measurements.append('e_'+line['name'])
    else:
        
        try:
            sigma = np.sqrt(np.power(FWHM_fin,2)-np.power(FWHM_ini,2))/2.355
            sigma = np.nan_to_num(sigma) #turn negative values to zero
            sigma = sigma.clip(0.01) # add a really small number instead of zero (code crashed otherwise)
            flux = varsmooth(x = wave, y = flux, sig_x = sigma)
            print('Convolution successfull from', FWHM_ini, 'to', FWHM_fin)
        except:
            print('Convolution not performed. Check FWHM ini and fin: ',FWHM_ini, FWHM_fin)

        for line in idx_definitions:
            try:
                (cont_l,cont_f,line_l,line_f)=GetConts(wave,flux,line['defs'],line['conts'])
                
                if path is not None:
                    fig, ax = plt.subplots()
                    fig.set_size_inches((5, 5))
                    ax.plot(wave[(wave >= np.min(line['conts'])) & (wave <=np.max(line['conts']))],
                            flux[(wave >= np.min(line['conts'])) & (wave <=np.max(line['conts']))], 'k-')
                    ax.axvspan(line['conts'][0],line['conts'][1], color='blue', alpha=0.5)
                    ax.axvspan(line['conts'][2],line['conts'][3], color='red', alpha=0.5)
                    vmin = np.min(flux[(wave >= np.min(line['conts'])) & (wave <=np.max(line['conts']))])
                    vmax = np.max(flux[(wave >= np.min(line['conts'])) & (wave <=np.max(line['conts']))])
                    ax.set_ylim(vmin-0.1*(vmax-vmin),vmax+0.1*(vmax-vmin))
                    ax.vlines(line['defs'], vmin-0.1*(vmax-vmin), vmax+0.1*(vmax-vmin),
                              linestyle='dashed', color='black')
                    vmin = np.min(np.append(cont_l,line_l))
                    vmax = np.max(np.append(cont_l,line_l))
                    ax.set_xlim(vmin-1,vmax+1)
                    name_fig=path+'/'+line['name']+'.png'
                    if line['defs'][0] == line['defs'][1]:
                        ax.hlines(cont_f[0], line['conts'][0], line['conts'][1], color='blue')
                        ax.hlines(cont_f[1], line['conts'][2], line['conts'][3], color='red')
                    else:
                        (a,b) = np.polyfit(cont_l,cont_f,deg=1)
                        cont = lambda x : x*a+b 
                        ax.plot(cont_l, cont_f, 'ko', markersize=1)
                        ax.plot(line_l, line_f, 'ko', markersize=1)
                        ax.plot(cont_l, cont(cont_l), 'g-')
                    ax.set_xlim(np.min(line['conts'])-1, np.max(line['conts'])+1)
                    ax.set_xlabel(r'$\lambda$')
                    ax.set_ylabel(r'Flux')
                    fig.tight_layout()
                    fig.savefig(name_fig, format='png')
                    plt.close(fig)
                
                if line['defs'][0] == line['defs'][1]:
                    EW = computeBREAK(red_l=cont_l[1],red_f=cont_f[1],blue_l=cont_l[0],blue_f=cont_f[0]) 
                else:
                    EW = computeEW(cont_l,cont_f,line_l,line_f)
                eEW = np.nan
                measurements.append(EW)
                head_measurements.append(line['name'])
                measurements.append(eEW)
                head_measurements.append('e_'+line['name'])
            
            except:
                measurements.append(np.nan)
                head_measurements.append(line['name'])
                measurements.append(np.nan)
                head_measurements.append('e_'+line['name'])

    return head_measurements, measurements