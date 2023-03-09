#!/usr/bin/env python

import re
import sys

from argparse import ArgumentParser

import DXEntity

dxcc = DXEntity.DXCC()

str_clean = re.compile(r'\W').sub
countries = {str_clean('', c).lower():c for c in dxcc.entities}

parser = ArgumentParser(description="Send e-QSL cards")
parser.add_argument("args", nargs="*")
opts = parser.parse_args()

if not opts.args:
  for country in countries:
    print(countries[country])
  sys.exit()

for ctry in (str_clean('', c).lower() for c in opts.args):
  if ctry in countries:
    print(f"{countries[ctry]} is a valid entity")
    continue
  ctry = ctry.upper()
  result = dxcc.lookup(ctry)
  if result.prefix == ctry:
    print(f"{ctry} = {result.country} - Continent: {result.continent}, CQZone: "
          f"{result.cqzone}, ITUZone: {result.ituzone}")
