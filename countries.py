#!/usr/bin/env python

import sys
import textwrap

from argparse import ArgumentParser

import DXEntity

dxcc = DXEntity.DXCC()

countries = dxcc.entities

wrapper = textwrap.TextWrapper()
wrapper.subsequent_indent = wrapper.initial_indent = " >  "

parser = ArgumentParser(description="Send e-QSL cards")
parser.add_argument("args", nargs="*")
opts = parser.parse_args()

if not opts.args:
  for country in sorted(countries):
    print(countries[country])
  sys.exit()

for ctry in opts.args:
  if ctry in countries:
    print(f"{ctry} is a valid entity")
    prefixes = ', '.join(dxcc.get_entity(ctry))
    print('\n'.join(wrapper.wrap(prefixes)))

    continue
  ctry = ctry.upper()
  try:
    result = dxcc.lookup(ctry)
    if ctry.startswith(result.prefix):
      print(f"{ctry} = {result.country} - Continent: {result.continent}, CQZone: "
            f"{result.cqzone}, ITUZone: {result.ituzone}")
  except KeyError as err:
    print(err)
