__author__ = 'Zach'

from math import *
import numpy as np

def ga2equ(ga):
    """
    Convert Galactic to Equatorial coordinates (J2000.0)
    (use at own risk)

    Input: [l,b] in decimal degrees
    Returns: [ra,dec] in decimal degrees

    Source:
    - Book: "Practical astronomy with your calculator" (Peter Duffett-Smith)
    - Wikipedia "Galactic coordinates"

    Tests (examples given on the Wikipedia page):
    >>> ga2equ([0.0, 0.0]).round(3)
    array([ 266.405,  -28.936])
    >>> ga2equ([359.9443056, -0.0461944444]).round(3)
    array([ 266.417,  -29.008])
    """
    l = radians(ga[0])
    b = radians(ga[1])

    # North galactic pole (J2000) -- according to Wikipedia
    pole_ra = radians(192.859508)
    pole_dec = radians(27.128336)
    posangle = radians(122.932-90.0)

    # North galactic pole (B1950)
    #pole_ra = radians(192.25)
    #pole_dec = radians(27.4)
    #posangle = radians(123.0-90.0)

    ra = atan2( (cos(b)*cos(l-posangle)), (sin(b)*cos(pole_dec) - cos(b)*sin(pole_dec)*sin(l-posangle)) ) + pole_ra
    dec = asin( cos(b)*cos(pole_dec)*sin(l-posangle) + sin(b)*sin(pole_dec) )

    return np.array([degrees(ra), degrees(dec)])

ga2equ([1,5])