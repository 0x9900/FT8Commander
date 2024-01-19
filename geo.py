#
# BSD 3-Clause License
#
# Copyright (c) 2021-2023, Fred W6BSD
# All rights reserved.
#
#
"""
Spherical geometry
"""

import math
from functools import lru_cache


def haversine(val):
  # The haversine formula determines the great-circle distance between two points
  return math.sin(val / 2) ** 2


def distance(orig, dest):
  """Calculate the distance between 2 coordinates"""
  radius = 6371  # Earth radius in meters
  lat1, lon1 = orig
  lat2, lon2 = dest

  dphi = math.radians(lat2 - lat1)
  dlambda = math.radians(lon2 - lon1)
  phi1, phi2 = math.radians(lat1), math.radians(lat2)

  axr = haversine(dphi) + math.cos(phi1) * math.cos(phi2) * haversine(dlambda)
  return 2 * radius * math.atan2(math.sqrt(axr), math.sqrt(1 - axr))


def azimuth(orig, dest):
  """Calculate the direction of the `dest` point from the `origin` """
  # pylint: disable=invalid-name
  lat1, lon1 = orig
  lat2, lon2 = dest

  d_lon = lon2 - lon1
  x = math.cos(math.radians(lat2)) * math.sin(math.radians(d_lon))
  y = (math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) -
       math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) *
       math.cos(math.radians(d_lon)))
  brng = math.atan2(x, y)
  brng = math.degrees(brng)
  return abs(int(brng))


@lru_cache(maxsize=1024)
def grid2latlon(maiden):
  """ Transform a maidenhead grid locator to latitude & longitude """
  if not maiden:
    return (0, 0)

  maiden = maiden.strip().upper()
  maiden_lg = len(maiden)
  if len(maiden) not in [2, 4, 6, 8]:
    raise RuntimeError('Locator length error: 2, 4, 6 or 8 characters accepted')

  char_a = ord("A")
  lon = -180.0
  lat = -90.0

  lon += (ord(maiden[0]) - char_a) * 20
  lat += (ord(maiden[1]) - char_a) * 10

  if maiden_lg >= 4:
    lon += int(maiden[2]) * 2
    lat += int(maiden[3])
  if maiden_lg >= 6:
    lon += (ord(maiden[4]) - char_a) * 5.0 / 60
    lat += (ord(maiden[5]) - char_a) * 2.5 / 60
  if maiden_lg >= 8:
    lon += int(maiden[6]) * 5.0 / 600
    lat += int(maiden[7]) * 2.5 / 600

  return lat, lon
