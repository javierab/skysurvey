# pylint: disable=E1101
# pylint: disable=C0325

'''
========================================================
util.py : Utility routines for the survey footprint code
========================================================

This module provides utility functions that are needed for the survey
footprint code, but are not unique to the survey footprint and might be
needed elsewhere

- :func:'wcs_to_healpix' converts a WCS fits file to a full sky Healpix map
- :func:'get_color_map' returns a color map that is a single color, but has
    a varying alpha (going from 0.5 to 1)
- :func:'bin_catalog' constructs a Healpix map with the map pixel value being
    the number of sources in that pixel
- :func:'gen_map_centersize' constructs a Healpix map where any pixel inside
    the rectangle defined by the center point and edge size is 1 and any
    point outside is 0
- :func:'gen_map_polygon' constructs a Healpix map where any pixel inside
    the polygon defined by the input vertices is 1 and any point outside is 0
- :func:'gen_map_disc' constructs a Healpix map where any pixel inside the
    disc defined by the input center point and disc radius is 1 and any point
    outside is 0.
- :func:'read_healpix_maps' reads in multiple Healpix maps, ensures there are
    of the same nside by upgrading or downgrading the maps, and sums them
    together.
- :func:'read_wcs_maps' reads in WCS fits files, converts the stored image
    to a Healpix format, and sums the different maps together.
'''

from __future__ import print_function

import numpy as np
import healpy as H
import astropy.wcs as wcs
from astropy.io import fits
from scipy.sparse import coo_matrix
import hashlib

# For differing imports between Python2 and Python3
try:
    import ConfigParser
    from urllib2 import urlopen
except ImportError:
    import configparser as ConfigParser
    from urllib.request import urlopen


def wcs_to_healpix(hdulist, nside):
    '''Converts data in an opened FITS file from a generic WCS to Healpix.

    Parameters
    ----------
    hdulist: hdu.hdulist.HDUList (astropy.io.fits or pyfits)
        The opened FITS file that we can't to convert to Healpix.

    nside: int
        The nside of the output Healpix ma[

    returns
    -------
    hpx_data: array-like
        A Healpix map

    Notes
    -----
    The steps for converting are to first find the ra/dec of ever pixel in
    the flat sky WCS map. Convert these position to theta/phi on the sphere.
    Then calculate the pixel number in the healpix map. Flat sky pixels with
    the same Healpix pixel number are summed over.
    '''

    wcs1 = wcs.WCS(hdulist[0].header)

    data = hdulist[0].data

    print("x/ysize = ", data.shape[0], data.shape[1])

    pixcrd = [(y, x) for x in xrange(data.shape[0]) for y in
              xrange(data.shape[1])]

#   pix2world to get ra/dec values of each pixel
    world = wcs1.wcs_pix2world(pixcrd, 1)

    pixcrd = np.array(pixcrd)

#   needed since in some ACT data the length of the map is >360 degrees
    idx = np.isfinite(world[:, 0])

    pixcrd = pixcrd[idx, :]
    world = world[idx, :]

#   Use Healpy to do ang2pix for Healpix pixel numbers
    theta = np.pi/2.0 - np.radians(world[:, 1])
    phi = np.radians(world[:, 0])
    pixnum = H.ang2pix(nside, theta, phi)

    npix = H.nside2npix(nside)

#   coo_matrix will sum entries that have multiple elements
    hpx_data = coo_matrix((data[(pixcrd[:, 1], pixcrd[:, 0])],
                           (pixnum, np.zeros_like(pixnum))),
                          shape=np.array([npix, 1])).A.transpose()
    hpx_data.shape = (npix)

    return hpx_data

def get_color_map(color):
    '''Generate a LinearSegmentedColormap with a single color and varying
    transparency. Bad values and values below the lower limit are set to be
    completely transparent.

    Parameters
    ----------
    color: string or array-like with shape (3,)
        The color to use when overlaying the survey footprint. Either a
        string that can be input to colorConverter.to_rgb() or rgb triplet.

    Returns
    -------
    colormap1: LinearSegmentedColormap
        A color map that is a single color but varies its opacity
        from 0.5 to 1. Bad values and values below the minimum are completely
        transparent.
    '''

    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.colors import colorConverter

#   if the type is a string it is assumed to be an input to allow us
#   to get an rgb value. If it is not a string and length is 3, it is
#   assumed to be an actual rgb value
    if isinstance(color, str):
        rgb = colorConverter.to_rgb(color)
    elif len(color) == 3:
        rgb = color
    else:
        raise ValueError('Bad color input')

    cdict = {'red':   [(0, rgb[0], rgb[0]),
                       (1, rgb[0], rgb[0])],
             'green': [(0, rgb[1], rgb[1]),
                       (1, rgb[1], rgb[1])],
             'blue':  [(0, rgb[2], rgb[2]),
                       (1, rgb[2], rgb[2])],
             'alpha': [(0, 0.5, 0.5),
                       (1, 1, 1)]}

    colormap1 = LinearSegmentedColormap('FootprintCM', cdict)
    colormap1.set_bad(alpha=0.0)
    colormap1.set_under(alpha=0.0)

    return colormap1

def bin_catalog(ra_rad, dec_rad, redshift, nside, z_left, z_right, coord='C'):
    '''Takes a catalog of ra,dec values for sources and generates a Healpix
    map with the pixel value corresponding to the number of sources located
    inside that pixel.

    Parameters
    ----------
    ra_rad : array-like
        The right ascension value in radians for each source

    dec_rad : array-like
        The declination value in radians for each source

    redshift : array-like
        The redshift for each source

    nside : int
        The nside of the output Healpix map

    z_left : float
        The smallest redshift for the sources added to the Healpix map

    z_right : float
        The largest redshift for the sources added to the Healpix map

    coord : 'C', 'E', or 'G'
        The coordinate system of the output map

    Returns
    -------
    overdensity : array-like

    nbar : array-like

    gal_counts : array-like

    gal_spatial : array-like

    '''

    npix = H.nside2npix(nside)
    nnu = len(z_left)
#   from Ra/dec to galactic
    rotate = H.rotator.Rotator(coord=['C', coord])
    theta, phi = rotate(dec_rad, ra_rad)

    gal_ind = H.pixelfunc.ang2pix(nside, theta, phi,
                                  nest=False)

#   spatial density
    gal_spatial = np.bincount(gal_ind, minlength=npix)

#   z binning
    gal_ring = np.zeros(shape=(npix, nnu))
    gal_counts = np.zeros_like(z_left)
    for ind in range(nnu):
        in_bin = np.logical_and(redshift > z_left[ind], redshift < z_right[ind])
        gal_bin = gal_ind[in_bin]
        gal_ring[:, ind] = np.bincount(gal_bin, minlength=npix)
        gal_counts[ind] = len(gal_bin)

#   make a separable selection function
    nbar = gal_spatial[:, None] * gal_counts[None, :]
    nbar *= np.sum(gal_counts) / np.sum(nbar)

    overdensity = (gal_ring - nbar) / nbar

    return overdensity, nbar, gal_counts, gal_spatial

def gen_map_centersize(center, size, nside):
    '''Generates a Healpix map with the only non-zero values defined by pixels
    inside the input rectangle.

    Parameters
    ----------
    center : array-like with shape (2,)
        The center lon,lat in degrees of the rectangle

    size : array-like with shape (2,)
        The length of the edge in lone,lat space of the rectangle in degrees

    nside : int
        The nside of the output Healpix map

    Returns
    -------
    hpx_map : array-like
        A Healpix map with non-zero values inside the rectangle.
    '''

    corner1 = (center[0]+size[0]/2.0, center[1]+size[1]/2.0)
    corner2 = (center[0]+size[0]/2.0, center[1]-size[1]/2.0)
    corner3 = (center[0]-size[0]/2.0, center[1]-size[1]/2.0)
    corner4 = (center[0]-size[0]/2.0, center[1]+size[1]/2.0)
    
    vertices = (corner1, corner2, corner3, corner4)

    lonra = [center[0]-size[0]/2.0, center[0]+size[0]/2.0]
    latra = [center[1]-size[1]/2.0, center[1]+size[1]/2.0]

#   hpx_map = gen_map_polygon(vertices, nside)
    hpx_map = gen_map_rectangle(lonra, latra, nside)

    return hpx_map

def gen_map_polygon(vertices, nside):
    '''Generates a Healpix map with the only non-zero values in the pixels
    inside the input polygon

    Parameters
    ----------
    vertices : array-like with shape (n,2) or (2,n)
        The lon,lat vertices of the polygon in degrees. n >= 3

    nside : int
        The nside of the output Healpix map

    Returns
    -------
    hpx_map : array-like
        A Healpix map with non-zero values inside the polygon
    '''

    vertices = np.array(vertices)

    if vertices.shape[1] != 2:
        vertices = np.transpose(vertices)
        if vertices.shape[1] != 2:
            raise ValueError("Need a n x 2 or 2 x n input vertices array")

    thetas = np.pi/2 - np.radians(vertices[:, 1])
    phis = np.radians(vertices[:, 0])

    vecs = H.ang2vec(thetas, phis)

    ipix = H.query_polygon(nside, vecs)

    hpx_map = np.zeros(H.nside2npix(nside))
    hpx_map[ipix] = 1.0

    return hpx_map

def gen_map_disc(radec_cen, rad, nside):
    '''Generates a Healpix map with the only non-zero values in the
    pixels inside the input disc.

    Parameters
    ----------
    radec_cen : array-like with shape (2,)
        The center ra,dec of the disc in degrees

    rad : float
        The radius of the disc in degrees

    nside : int
        The nside of the output Healpix map

    Returns
    -------
    hpx_map : array-like
        A Healpix map with non-zero values inside the disc
    '''

    theta = np.pi/2 - np.radians(radec_cen[1])
    phi = np.radians(radec_cen[0])

    vec = H.ang2vec(theta, phi)

    ipix = H.query_disc(nside, vec, np.radians(rad))

    hpx_map = np.zeros(H.nside2npix(nside))
    hpx_map[ipix] = 1.0

    return hpx_map

def gen_map_rectangle(lonra, latra, nside):
    '''Generates a Healpix map with the only non-zero values in the
    pixels inside a rectangle oriented along the lon/lat lines.

    Parameters
    ----------
    lonra : array-like with shape (2,)
        The range of longitude in degrees

    latra : array-like with shape (2,)
        The range of latitude in degrees

    nside : int
        The nside of the output Healpix map

    Returns
    -------
    hpx_map: array-like
        A Healpix map with non-zero values inside the disc
    '''

#   Make sure we first value is smaller than second value
    if lonra[1] < lonra[0]:
        lonra = [lonra[0] - 360.0, lonra[1]]

    npix = H.nside2npix(nside)

    hpx_map = np.zeros(npix)

    ipix = np.arange(npix)
    theta, phi = H.pix2ang(nside, ipix)
    
    lon = np.degrees(phi)
    lat = 90.0 - np.degrees(theta)

#   Make sure that range of lon matches goes through values on lonra
    lon[lon > lonra[1]] -= 360.0

    idx = np.all([[lat >= latra[0]], [lat <= latra[1]], [lon >= lonra[0]], [lon <= lonra[1]]], axis=0)
    idx.shape = (npix,)

    hpx_map[idx] = 1.0

    return hpx_map

def gen_map_strip(mindec, maxdec, nside):
    '''Generates a Healpix map with the only non-zero values in the
    pixels inside a strip between the input declinations/latitudes

    Parameters
    ----------
    mindec : float
        Minimum declination/latitude in degrees

    maxdec : float
        Maximum declinaton/latitude in degrees

    nside : int
        The nside of the output Healpix map

    Returns
    -------
    hpx_map: array-like
        A healpix map with the non-zero values inside the strip
    '''

    theta1 = np.radians(90.0 - maxdec)
    theta2 = np.radians(90.0 - mindec)

    if theta2 < theta1:
        theta1, theta2 = theta2, theta2

    npix = H.nside2npix(nside)

    hpx_map =np.zeros(npix)

    ipix = H.query_strip(nside, theta1, theta2)

    hpx_map[ipix] = 1.0

    return hpx_map

def read_hpx_maps(fns):
    '''Read in one or more healpix maps and add them together. Must input
    an array of strings even if only inputting a single map.

    Parameters
    ----------
    fns : list of strings
        The filenames for the healpix maps to read in.

    Returns
    -------
    hpx_map: array-like
        A healpix map that is the sum of the Healpix maps in the input files.

    Notes
    -----
    The nside of the output map will be the nside of the file map in the list.
    Every other map will be upgraded or downgraded that that nside value.
    '''

    hpx_map = H.read_map(fns[0], verbose=False)
    nside = H.npix2nside(len(hpx_map))
    for fn_tmp in fns[1:]:
        tmp_map = H.read_map(fn_tmp, verbose=False)
        hpx_map += H.ud_grade(tmp_map, nside)

    return hpx_map

def read_wcs_maps(fns, nside):
    '''Read in WCS FITS files and convert them to a Healpix map.

    Parameters
    ----------
    fns : list of strings
        The filenames for the WCS maps to read in.

    nside : int
        The nside of the output map.

    Returns
    -------
    hpx_map : array-like
        The WCS maps read in and converted to healpix format
    '''

    hpx_map = np.zeros(H.nside2npix(nside))
    for fn_tmp in fns:
        hdulist = fits.open(fn_tmp)
        hpx_map += wcs_to_healpix(hdulist, nside)
        hdulist.close()

    return hpx_map

def download_url(url, checksum, local_path):

    req = urlopen(url)
    file_chunk = 16 * 1024
    with open(local_path, 'wb') as fp1:
        while True:
            chunk = req.read(file_chunk)
            if not chunk:
                break
            fp1.write(chunk)

    cksum_file = hashlib.md5(open(local_path, 'rb').read()).hexdigest()
    if checksum != cksum_file:
        raise ValueError("Remote file checksum does not match cfg checksum:", checksum, cksum_file)

    return True

