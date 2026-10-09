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

def _interp_row(l_obs, x):
    '''Weights of the pixels of l_obs in the linear interpolation at x (None if x is outside).'''
    if x < l_obs[0] or x > l_obs[-1]:
        return None
    row = np.zeros(len(l_obs))
    i = min(np.searchsorted(l_obs, x, side='right') - 1, len(l_obs) - 2)
    t = (x - l_obs[i]) / (l_obs[i+1] - l_obs[i])
    row[i] += 1 - t
    row[i+1] += t
    return row


def _sample_operator(l_obs, lo, hi, closed):
    '''
    Wavelengths and (n_points x n_pixels) linear operator giving the flux at the
    points GetConts uses within [lo, hi]: the interpolated edges and the pixels in
    between (pixels on the edges are included only if closed is True).
    '''
    inside = (l_obs >= lo) & (l_obs <= hi) if closed else (l_obs > lo) & (l_obs < hi)
    rows, waves = [], []
    first = _interp_row(l_obs, lo)
    if first is not None:
        rows.append(first)
        waves.append(lo)
    for i in np.where(inside)[0]:
        row = np.zeros(len(l_obs))
        row[i] = 1.
        rows.append(row)
        waves.append(l_obs[i])
    last = _interp_row(l_obs, hi)
    if last is not None:
        rows.append(last)
        waves.append(hi)
    return np.array(waves), np.array(rows)


def _trapezoid_weights(x):
    '''Weights w such that sum(w*y) is the trapezoidal integral of y(x).'''
    w = np.zeros(len(x))
    dx = np.diff(x)
    w[:-1] += dx / 2
    w[1:] += dx / 2
    return w


def index_error(l_obs, f_obs, sigma, linelims, contBandPass):
    '''
    Uncertainty of an index (EW or break) obtained by propagating, to first order,
    the uncertainties of the pixels through the exact same operations performed by
    GetConts and computeEW/computeBREAK: interpolated band edges, mean fluxes of the
    continuum bands (trapezoidal rule), linear least-squares pseudo-continuum and
    trapezoidal integration of 1 - F/Fc over the central band. Pixel uncertainties
    are assumed to be uncorrelated:  sigma_I^2 = sum_i (dI/dF_i)^2 sigma_i^2.

    Parameters:
    l_obs, f_obs: wavelength and flux arrays of the spectrum
    sigma: uncertainty of each pixel (array) or the same value for all pixels
    linelims: limits of the central band (equal limits for a break)
    contBandPass: limits of the continuum bands, pair-wise
    '''
    l_obs = np.asarray(l_obs, dtype=float)
    f_obs = np.asarray(f_obs, dtype=float)
    sigma = np.broadcast_to(np.asarray(sigma, dtype=float), l_obs.shape)

    # restrict everything to the pixels that can enter the index
    lo = min(np.min(contBandPass), linelims[0])
    hi = max(np.max(contBandPass), linelims[1])
    i0 = max(np.searchsorted(l_obs, lo) - 1, 0)
    i1 = min(np.searchsorted(l_obs, hi) + 1, len(l_obs))
    l_obs, f_obs, sigma = l_obs[i0:i1], f_obs[i0:i1], sigma[i0:i1]

    # mean flux of each continuum band: C = U F, at the band mid-points lam_c
    U, lam_c = [], []
    for k in range(len(contBandPass) // 2):
        x, S = _sample_operator(l_obs, contBandPass[2*k], contBandPass[2*k+1], closed=False)
        U.append(_trapezoid_weights(x) @ S / (x[-1] - x[0]))
        lam_c.append((x[-1] + x[0]) / 2.)
    U, lam_c = np.array(U), np.array(lam_c)
    C = U @ f_obs

    if linelims[0] == linelims[1]:
        # break: D = C_red / C_blue
        D = C[1] / C[0]
        grad = U[1] / C[0] - D * U[0] / C[0]
        return float(np.sqrt(np.sum((grad * sigma)**2)))

    # central band: line flux F_j = L F at the wavelengths lam_l
    lam_l, L = _sample_operator(l_obs, linelims[0], linelims[1], closed=True)
    # linear least-squares pseudo-continuum: Fc_j = A C = (A U) F
    X = np.column_stack([lam_c, np.ones_like(lam_c)])
    A = np.column_stack([lam_l, np.ones_like(lam_l)]) @ np.linalg.pinv(X)
    AU = A @ U
    F_line, F_cont = L @ f_obs, AU @ f_obs
    t = _trapezoid_weights(lam_l)
    # EW = sum_j t_j (1 - F_j/Fc_j)  ->  dEW/dF_i
    grad = -(t / F_cont) @ L + (t * F_line / F_cont**2) @ AU
    return float(np.sqrt(np.sum((grad * sigma)**2)))


def bad_pixels(wave, flux, error=None, mask=None, mask_regions=None):
    '''
    Boolean array, True for the pixels that must not be used in the measurements.

    Parameters:
    wave, flux: wavelength and flux arrays of the spectrum
    error: error spectrum (optional). Pixels with non-finite or non-positive errors are
        flagged, unless all the errors are non-positive (i.e. no real error spectrum).
    mask: array with the same size as wave, True (or non-zero) for bad pixels (optional)
    mask_regions: list of (lambda_min, lambda_max) intervals to be masked, in the same
        frame as wave, e.g. emission lines or sky residuals (optional)
    '''
    wave = np.asarray(wave, dtype=float)
    bad = ~np.isfinite(np.asarray(flux, dtype=float))
    if isinstance(error, np.ndarray):
        err = np.asarray(error, dtype=float)
        bad |= ~np.isfinite(err)
        if (err > 0).any():
            bad |= ~(err > 0)
    if mask is not None:
        mask = np.asarray(mask)
        if mask.shape != wave.shape:
            raise ValueError(f"mask has {mask.size} values but the spectrum has {wave.size} pixels")
        bad |= mask.astype(bool)
    if mask_regions is not None:
        for lo, hi in np.atleast_2d(np.asarray(mask_regions, dtype=float)):
            bad |= (wave >= min(lo, hi)) & (wave <= max(lo, hi))
    return bad


def _bad_pixel_ratio(wave, bad, line):
    '''
    Fraction of bad pixels within the bandpasses of an index (central and continuum
    bands), and fraction of bad pixels within the central band alone.
    '''
    limits = np.append(line['defs'], line['conts']).reshape(-1, 2)
    inside = np.zeros_like(bad)
    for lo, hi in limits:
        inside |= (wave > lo) & (wave < hi)
    central = (wave > line['defs'][0]) & (wave < line['defs'][1])
    bpr = bad[inside].mean() if inside.any() else 0.
    bpr_central = bad[central].mean() if central.any() else 0.
    return bpr, bpr_central


def _mean_flux_error(wave, error, lo, hi):
    '''Uncertainty of the mean flux within [lo, hi], for uncorrelated pixel errors.'''
    inside = (wave >= lo) & (wave <= hi)
    return np.sqrt(np.sum(error[inside]**2)) / np.sum(inside)


def vollmann_error(EW, dl, SN):
    '''
    EW uncertainty from Vollmann & Eversberg (2006), Astron. Nachr., DOI 10.1002/asna.2006
    (https://arxiv.org/pdf/astro-ph/0606341.pdf); their equation (7) written as a function
    of the EW, the width of the central band (dl) and the S/N of the mean flux only.
    '''
    return np.sqrt((2*dl-EW)*(dl-EW))/SN


def _residual_rms(wave, flux, lo, hi):
    '''Noise per pixel: RMS of the residuals of a straight line fitted to the pixels in [lo, hi].'''
    (_, _, band_l, band_f) = GetConts(wave, flux, [lo, hi], [lo, hi])
    (a, b) = np.polyfit(band_l, band_f, deg=1)
    return np.std(band_f - (a*band_l + b))


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
        mask=None,
        mask_regions=None,
        bpr_thres=1.0,
        error_method='vollmann',
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
    # mask: array with the same size as wave, True (or non-zero) for bad pixels.
    # mask_regions: list of (lambda_min, lambda_max) intervals to be masked, in the rest frame.
    # error_method: analytic uncertainties (when simulate is None): 'vollmann' (default), from the
    #   S/N of the mean flux and the formula of Vollmann & Eversberg (2006), or 'propagation', the
    #   first-order propagation of the pixel uncertainties through the measurement (index_error).
    # bpr_thres: bad pixel ratio (fraction of bad pixels within the bandpasses of an index)
    #   above which the index is not measured (returned as NaN), as in pyLick (Borghi et al. 2022).
    #   Indices with all the pixels of the central band bad are never measured.
    # Bad pixels (mask, mask_regions, non-finite fluxes, and non-finite or non-positive
    #   errors) are replaced by a linear interpolation of the good ones (the variance, in the
    #   case of the error spectrum) before any other operation.
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


    if error_method not in ('vollmann', 'propagation'):
        raise ValueError(f"error_method must be 'vollmann' or 'propagation' (got '{error_method}').")

    #redshift correction
    if not _is_missing(z):
        wave = wave/(1+z)

    # bad pixels: replaced by a linear interpolation of the good ones
    bad = bad_pixels(wave, flux, error, mask, mask_regions)
    if bad.any():
        good = ~bad
        if good.sum() < 2:
            raise ValueError("Fewer than two good pixels in the spectrum.")
        flux = np.array(flux, dtype=float)
        flux[bad] = np.interp(wave[bad], wave[good], flux[good])
        if isinstance(error, np.ndarray):
            error = np.array(error, dtype=float)
            error[bad] = np.sqrt(np.interp(wave[bad], wave[good], error[good]**2))
        print(f'{bad.sum()} bad pixels masked and interpolated')
    else:
        bad = None

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
                    elif error_method == 'propagation':
                        # first-order propagation of the error spectrum (index_error)
                        eEW = index_error(wave, flux, error, line['defs'], line['conts'])
                    else:
                        # uncertainties of the mean fluxes in the blue and red bands
                        err_blue = _mean_flux_error(wave, error, line['conts'][0], line['conts'][1])
                        err_red = _mean_flux_error(wave, error, line['conts'][2], line['conts'][3])
                        eEW = EW * np.sqrt((err_blue/cont_f[0])**2+(err_red/cont_f[1])**2)
                else:
                    EW = computeEW(cont_l,cont_f,line_l,line_f) # No caso do simulate a EW deveria ser amedia e o erro o std....############NOTA#############
                    if simulate is not None:
                        eEW=[]
                        for i in range(simulate):
                            (cont_l,cont_f,line_l,line_f)=GetConts(wave,sim_flux[i,:],line['defs'],line['conts'])
                            eEW.append(computeEW(cont_l,cont_f,line_l,line_f))
                        eEW = np.std(eEW)
                    elif error_method == 'propagation':
                        # first-order propagation of the error spectrum (index_error)
                        eEW = index_error(wave, flux, error, line['defs'], line['conts'])
                    else:
                        (cont_l,err_cont,line_l,err_f)=GetConts(wave,error,line['defs'],line['conts'])
                        # S/N of the mean flux in the central bandpass (not the S/N per pixel):
                        # mean flux / uncertainty of the mean, sqrt(sum(sigma_i^2))/N
                        SN = np.mean(line_f) / (np.sqrt(np.sum(err_f**2)) / len(err_f))
                        dl = line_l[-1]-line_l[0]
                        eEW = vollmann_error(EW, dl, SN)
                if bad is not None:
                    bpr, bpr_central = _bad_pixel_ratio(wave, bad, line)
                    if bpr > bpr_thres or bpr_central >= 1:
                        print(f"Index {line['name']} not measured: {100*bpr:.0f}% of bad pixels in its bandpasses")
                        EW, eEW = np.nan, np.nan
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
                        # noise per pixel estimated from each continuum band, then propagated
                        rms_blue = _residual_rms(wave, flux, line['conts'][0], line['conts'][1])
                        rms_red = _residual_rms(wave, flux, line['conts'][2], line['conts'][3])
                        if error_method == 'propagation':
                            noise = np.where(wave < (line['conts'][1] + line['conts'][2]) / 2, rms_blue, rms_red)
                            eEW = index_error(wave, flux, noise, line['defs'], line['conts'])
                        else:
                            # uncertainties of the mean fluxes: RMS / sqrt(number of pixels in the band)
                            n_blue = np.sum((wave > line['conts'][0]) & (wave < line['conts'][1])) + 2
                            n_red = np.sum((wave > line['conts'][2]) & (wave < line['conts'][3])) + 2
                            eEW = EW*np.sqrt((rms_blue/np.sqrt(n_blue)/cont_f[0])**2+(rms_red/np.sqrt(n_red)/cont_f[1])**2)

                else:
                    EW = computeEW(cont_l,cont_f,line_l,line_f)
                    if error:
                        # noise per pixel estimated from the blue continuum band, then propagated
                        rms_blue = _residual_rms(wave, flux, line['conts'][0], line['conts'][1])
                        if error_method == 'propagation':
                            eEW = index_error(wave, flux, rms_blue, line['defs'], line['conts'])
                        else:
                            SN = cont_f[0] / (rms_blue / np.sqrt(len(line_l)))   # S/N of the mean flux in the line
                            dl = line['defs'][1] - line['defs'][0]
                            eEW = vollmann_error(EW, dl, SN)
                if bad is not None:
                    bpr, bpr_central = _bad_pixel_ratio(wave, bad, line)
                    if bpr > bpr_thres or bpr_central >= 1:
                        print(f"Index {line['name']} not measured: {100*bpr:.0f}% of bad pixels in its bandpasses")
                        EW, eEW = np.nan, np.nan
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