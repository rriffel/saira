import numpy as np
import matplotlib
matplotlib.use('Agg')  # figures are only ever saved to disk, never shown; the interactive
                        # Qt backend is unsafe when saira() runs in the GUI's worker QThread
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
    defs = np.array([np.array(re.findall(r"(?:\d*\.*\d+)", t), dtype='<f8') for t in file[:,1].astype(str)]) # geting the feature definition (always two values)
    conts = [np.array(re.findall(r"(?:\d*\.*\d+)", t), dtype='<f8') for t in file[:,2].astype(str)]# getting the continuum bands (any even number of values)
    try:
        refs = np.array([re.findall(r'\S+', t)[0] for t in file[:,3].astype(str)]) #getting the refs
    except:
        refs = np.full(len(names), "not defined")

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

def _is_missing(value):
    '''True for None and for a scalar NaN (e.g. an empty cell of the input table).'''
    if value is None:
        return True
    try:
        return bool(np.ndim(value) == 0 and np.isnan(value))
    except TypeError:
        return False


def read_resolution_curve(value, wave):
    '''
    Returns a resolution value (sigma, FWHM or R) for every pixel of wave.

    Parameters:
    value: a number (constant resolution); a 1D array with the same size as wave;
        a 2D array or the path to an ascii file whose first two columns are the
        wavelength (A) and the resolution value. Curves are linearly interpolated
        onto wave and kept constant beyond their limits.
    wave: wavelength array of the spectrum
    '''
    if isinstance(value, str):
        data = np.genfromtxt(value, comments='#')
        if data.ndim != 2 or data.shape[1] < 2 or np.isnan(data[:, 0]).all():
            raise ValueError(
                f"Resolution file '{value}' must have at least two numeric columns: "
                f"wavelength (A) and resolution value. Tables with one value per spectrum "
                f"(file, value) are only accepted for the initial resolution and the redshift."
            )
        value = data[:, :2]

    arr = np.asarray(value, dtype=float)
    if arr.ndim == 0:
        return float(arr)
    if arr.ndim == 2:
        arr = arr[np.isfinite(arr).all(axis=1)]
        order = np.argsort(arr[:, 0])
        return np.interp(wave, arr[order, 0], arr[order, 1])
    if arr.shape == np.shape(wave):
        return arr
    raise ValueError(
        f"Resolution array has {arr.size} values but the spectrum has {np.size(wave)} pixels; "
        f"give a (wavelength, value) curve instead."
    )


def resolution_to_fwhm(wave, sigma=None, R=None, FWHM=None):
    '''
    Converts a resolution given as sigma (km/s), R (lambda/d_lambda) or FWHM (A) into a
    FWHM (A) for every pixel of wave. If more than one is given, sigma takes precedence
    over R, and R over FWHM. Returns None if none is given.
    '''
    if not _is_missing(sigma):
        return (read_resolution_curve(sigma, wave)*2.355/c)*wave
    if not _is_missing(R):
        return np.divide(wave, read_resolution_curve(R, wave))
    if not _is_missing(FWHM):
        return read_resolution_curve(FWHM, wave)
    return None


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

def plotInd(line,
            path,
            wave,
            flux,
            old_flux,
            FWHM_ini,
            FWHM_fin,
            cont_l,
            cont_f,
            line_l,
            line_f,
            ):
    name_fig=path+'/'+line['name']+'.png'
  
    fig, ax = plt.subplots()
    fig.set_size_inches((5, 5))
    if (np.append(FWHM_ini,FWHM_fin) != None).all():
        ax.plot(wave[(wave >= np.min(line['conts'])) & (wave <=np.max(line['conts']))],
                old_flux[(wave >= np.min(line['conts'])) & (wave <=np.max(line['conts']))], 'k-')

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
    
   
    if line['defs'][0] == line['defs'][1]:
        ax.hlines(cont_f[0], line['conts'][0], line['conts'][1], color='blue')
        ax.hlines(cont_f[1], line['conts'][2], line['conts'][3], color='red')
    else:
        (a,b) = np.polyfit(cont_l,cont_f,deg=1)
        cont = lambda x : x*a+b 
        #ax.plot(cont_l, cont_f, 'ko', markersize=1)
        ax.plot(line_l, line_f,marker='o',color='purple', markersize=2)
        ax.plot([np.min(line['conts']),np.max(line['conts'])],
                    [cont(np.min(line['conts'])),cont(np.max(line['conts']))], 'g-')
    ax.set_xlim(np.min(line['conts'])-1, np.max(line['conts'])+1)
    ax.set_xlabel(r'$\lambda$')
    ax.set_ylabel(r'Flux')
    ax.set_title(line['name'])
    fig.tight_layout()
    fig.savefig(name_fig, format='png')
    plt.close(fig)



def plotIndSingle(line,
            wave,
            flux,
            old_flux,
            FWHM_ini,
            FWHM_fin,
            cont_l,
            cont_f,
            line_l,
            line_f,
            ax,
            ):
    if (np.append(FWHM_ini,FWHM_fin) != None).all():
        ax.plot(wave[(wave >= np.min(line['conts'])) & (wave <=np.max(line['conts']))],
                old_flux[(wave >= np.min(line['conts'])) & (wave <=np.max(line['conts']))], 'k-')

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
    
   
    if line['defs'][0] == line['defs'][1]:
        ax.hlines(cont_f[0], line['conts'][0], line['conts'][1], color='blue')
        ax.hlines(cont_f[1], line['conts'][2], line['conts'][3], color='red')
    else:
        (a,b) = np.polyfit(cont_l,cont_f,deg=1)
        cont = lambda x : x*a+b 
        #ax.plot(cont_l, cont_f, 'ko', markersize=1)
        ax.plot(line_l, line_f,marker='o',color='purple', markersize=2)
        ax.plot([np.min(line['conts']),np.max(line['conts'])],
                    [cont(np.min(line['conts'])),cont(np.max(line['conts']))], 'g-')
    ax.set_xlim(np.min(line['conts'])-1, np.max(line['conts'])+1)
    ax.set_xlabel(r'$\lambda$')
    ax.set_ylabel(r'Flux')
    ax.set_title(line['name'])




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
        path=None,
        AllIndicesPlot=None,
        negative_Ew_to_zero=False,
        ):
    
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

    # Creating a single plot (if required)

    try:
        tmp = idx_definitions.dtype
    except AttributeError:
        idx_definitions = read_idx_defs(idx_definitions)

    if AllIndicesPlot is not None:
        num_cols = 4 # fixed 4 columns
        num_plots=len(idx_definitions) 
        num_rows = (num_plots + num_cols - 1) // num_cols  # Calculate number of rows 
        fig, axes = plt.subplots(num_rows, num_cols, figsize=(15, 5*num_rows)) 


    #redshift correction
    if not _is_missing(z):
        wave = wave/(1+z)

    # converting sigma, R or FWHM (scalars, arrays or wavelength-dependent curves) to FWHM in A
    FWHM_ini = resolution_to_fwhm(wave, sigma=sigma_ini, R=R_ini, FWHM=FWHM_ini)
    FWHM_fin = resolution_to_fwhm(wave, sigma=sigma_fin, R=R_fin, FWHM=FWHM_fin)

    # Validate resolution parameters before convolution
    if (FWHM_ini is not None) and (FWHM_fin is not None):
        try:
            f_ini_arr = np.asarray(FWHM_ini, dtype=float)
            f_fin_arr = np.asarray(FWHM_fin, dtype=float)
            if np.all(f_fin_arr < f_ini_arr):
                raise ValueError(
                    f"Invalid resolution: target resolution is higher than initial resolution "
                    f"(mean FWHM_fin={np.mean(f_fin_arr):.3f} Å < mean FWHM_ini={np.mean(f_ini_arr):.3f} Å). "
                    f"Spectral convolution can only degrade resolution (FWHM_fin >= FWHM_ini)."
                )
        except TypeError:
            pass

    measurements = []
    head_measurements = []
    old_flux = np.copy(flux)
    
    if (FWHM_ini is not None) and (FWHM_fin is not None):
        try:
            diff2 = np.power(FWHM_fin, 2) - np.power(FWHM_ini, 2)
            if np.all(diff2 < 0):
                raise ValueError(
                    f"Cannot convolve: FWHM_fin < FWHM_ini. Final resolution is higher than initial resolution."
                )
            diff2 = np.clip(diff2, 0, None)
            sigma = np.sqrt(diff2) / 2.355
            sigma = np.nan_to_num(sigma).clip(0.01)
            flux_new = varsmooth(x=wave, y=flux, sig_x=sigma)
            if isinstance(error, np.ndarray):
                error_new = varsmooth_error(x=wave, error=error, sig_x=sigma)
                old_error = np.copy(error)
                error = error_new
            print(f'Convolution successful from FWHM_ini={np.mean(FWHM_ini):.3f} Å to FWHM_fin={np.mean(FWHM_fin):.3f} Å')
            old_flux = np.copy(flux)
            flux = flux_new
        except ValueError as ve:
            print(f'Resolution error: {ve}')
            raise ve
        except Exception as e:
            print('Convolution not performed. Check FWHM ini and fin: ', FWHM_ini, FWHM_fin, e)

    if isinstance(error, np.ndarray): # test if the user provided an error spectrum
        if simulate is not None:
            error[np.where(error <= 0)] = 1e-20
            sim_flux=np.random.normal(flux,error, size=(simulate, len(flux)))
            print(simulate,'spectra were created')
        
         
        plt_pos=0
        for line in idx_definitions:
        
            try:
                (cont_l,cont_f,line_l,line_f)=GetConts(wave,flux,line['defs'],line['conts'])
                ax = None
                name_fig = None
                # this is to do the plots
                if path is not None:
                    plotInd(line=line,
                    path=path,
                    wave=wave,
                    flux=flux,
                    old_flux=old_flux,
                    FWHM_ini=FWHM_ini,
                    FWHM_fin=FWHM_fin,
                    cont_l=cont_l,
                    cont_f=cont_f,
                    line_l=line_l,
                    line_f=line_f
                    )
                if AllIndicesPlot is not None:
                    plotIndSingle(line=line,
                    wave=wave,
                    flux=flux,
                    old_flux=old_flux,
                    FWHM_ini=FWHM_ini,
                    FWHM_fin=FWHM_fin,
                    cont_l=cont_l,
                    cont_f=cont_f,
                    line_l=line_l,
                    line_f=line_f,
                    ax=axes.flatten()[plt_pos],
                    )
                    plt_pos += 1


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
                    EW = computeEW(cont_l,cont_f,line_l,line_f) # No caso do simulate a EW deveria ser amedia e o erro o std....############NOTA#############
                    if simulate is not None:
                        eEW=[]
                        for i in range(simulate):
                            (cont_l,cont_f,line_l,line_f)=GetConts(wave,sim_flux[i,:],line['defs'],line['conts'])
                            eEW.append(computeEW(cont_l,cont_f,line_l,line_f))
                        eEW = np.std(eEW)
                    else:
                        (cont_l,err_cont,line_l,err_f)=GetConts(wave,error,line['defs'],line['conts']) # Parece nao estar funcionando ######################NOTA #########################
                        S=line_f
                        N=err_f
                        SN=np.mean(np.divide(S,N))
                        dl = line_l[-1]-line_l[0]
                        eEW = np.sqrt((2*dl-EW)*(dl-EW))/SN
                        # error bar estimation based on Vollmann & Eversberg (2006),
                        # Astron. Nachr., DOI 10.1002/asna.2006
                        # https://arxiv.org/pdf/astro-ph/0606341.pdf
                        # (changed their equation (7) to depend only on EQW, d_LAMBDA and the S/N)
                if negative_Ew_to_zero:
                    if float(EW) < 0:
                        EW = 0.00
                        eEW = 0.00

                
                measurements.append(EW)
                head_measurements.append(line['name'])
                measurements.append(eEW)
                head_measurements.append('e_'+line['name'])
            except Exception as e:
                print(f"Failed to measure/plot index {line['name']}: {e}")
                measurements.append(np.nan)
                head_measurements.append(line['name'])
                measurements.append(np.nan)
                head_measurements.append('e_'+line['name'])
    else:
        plt_pos=0
        for line in idx_definitions:
           
            try:
                (cont_l,cont_f,line_l,line_f)=GetConts(wave,flux,line['defs'],line['conts'])
                # this is to do the plots
                if path is not None:
                    plotInd(line=line,
                    path=path,
                    wave=wave,
                    flux=flux,
                    old_flux=old_flux,
                    FWHM_ini=FWHM_ini,
                    FWHM_fin=FWHM_fin,
                    cont_l=cont_l,
                    cont_f=cont_f,
                    line_l=line_l,
                    line_f=line_f
                    )
                if AllIndicesPlot is not None:
                    plotIndSingle(line=line,
                    wave=wave,
                    flux=flux,
                    old_flux=old_flux,
                    FWHM_ini=FWHM_ini,
                    FWHM_fin=FWHM_fin,
                    cont_l=cont_l,
                    cont_f=cont_f,
                    line_l=line_l,
                    line_f=line_f,
                    ax=axes.flatten()[plt_pos],
                    )
                    plt_pos += 1




                eEW = np.nan
                if line['defs'][0] == line['defs'][1]:
                    EW = computeBREAK(red_l=cont_l[1],red_f=cont_f[1],blue_l=cont_l[0],blue_f=cont_f[0])
                    if error:
                        (w_mean,s_blue,cont_wave,cont_flux) = GetConts(wave,flux,line['conts'][0:2],line['conts'][0:2])
                        (a,b) = np.polyfit(cont_wave,cont_flux,deg=1)
                        cont = lambda x : x*a+b
                        err_blue = np.std(cont_flux-cont(cont_wave))
                        (w_mean,s_red,cont_wave,cont_flux) = GetConts(wave,flux,line['conts'][2:4],line['conts'][2:4])
                        (a,b) = np.polyfit(cont_wave,cont_flux,deg=1)
                        cont = lambda x : x*a+b
                        err_red = np.std(cont_flux-cont(cont_wave))
                        eEW = EW*np.sqrt((err_blue/s_blue[0])**2+(err_red/s_red[0])**2)

                else:
                    EW = computeEW(cont_l,cont_f,line_l,line_f)
                    if error:
                        (w_mean,s_mean,cont_wave,cont_flux) = GetConts(wave,flux,line['conts'][0:2],line['conts'][0:2])
                        (a,b) = np.polyfit(cont_wave,cont_flux,deg=1)
                        cont = lambda x : x*a+b
                        S = s_mean[0]
                        N = np.std(cont_flux-cont(cont_wave))
                        SN = S/N
                        dl = line['defs'][1] - line['defs'][0]
                        eEW = np.sqrt((2*dl-EW)*(dl-EW))/SN
                if negative_Ew_to_zero:
                    if float(EW) < 0:
                        EW = 0.00
                        eEW=0.00
                
                
                
                measurements.append(EW)
                head_measurements.append(line['name'])
                measurements.append(eEW)
                head_measurements.append('e_'+line['name'])

            except Exception as e:
                print(f"Failed to measure/plot index {line['name']}: {e}")
                measurements.append(np.nan)
                head_measurements.append(line['name'])
                measurements.append(np.nan)
                head_measurements.append('e_'+line['name'])

    # save the combined all-indices figure regardless of whether individual
    # indices failed above (a failure must not prevent the figure from being saved)
    if AllIndicesPlot is not None:
        fig.tight_layout()
        fig.savefig(AllIndicesPlot, format='png')
        plt.close(fig)
        print(f'All-indices figure saved: {AllIndicesPlot}')

    return head_measurements, measurements