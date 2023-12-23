#!/usr/bin/env python


import os
import sys
import textwrap
from argparse import ArgumentParser

import DXEntity


def clist():
  dxcc = DXEntity.DXCC()
  countries = dxcc.entities
  for _country in sorted(countries):
    print(_country)

def get_prefix(prefix):
  # pylint: disable=no-member
  dxcc = DXEntity.DXCC()
  prefix = prefix.upper()
  match, result = dxcc.get_prefix(prefix)
  print(f"Call prefix: {match} > {result.prefix} = {result.country} - Continent: "
        f"{result.continent}, CQZone: "
        f"{result.cqzone}, ITUZone: {result.ituzone}")

def check(ctry):
  dxcc = DXEntity.DXCC()
  ctry = ctry.upper()
  countries = {k.upper(): k for k in dxcc.entities}
  if ctry not in countries:
    raise KeyError(f'The country "{ctry}" cannot be found.')
  print(f'Country "{countries[ctry]}" found.')

def country(ctry):
  dxcc = DXEntity.DXCC()
  wrapper = textwrap.TextWrapper()
  wrapper.subsequent_indent = wrapper.initial_indent = " >  "

  ctry = ctry.upper()
  countries = {k.upper(): k for k in dxcc.entities}
  if ctry not in countries:
    raise KeyError(f'The country "{countries[ctry]}" cannot be found.')

  ctry = countries[ctry]
  prefixes = ', '.join(dxcc.get_entity(ctry))
  print('\n'.join(wrapper.wrap(prefixes)))

def main():
  parser = ArgumentParser(description="DXCC entities lookup")
  x_grp = parser.add_mutually_exclusive_group(required=True)
  x_grp.add_argument("-l", "--list", action="store_true", default=False,
                     help="List all the countries")
  x_grp.add_argument("-c", "--country", type=str,
                     help="Find the country from a callsign")
  x_grp.add_argument("-C", "--check", type=str,
                     help="Check if the country from a exists")
  x_grp.add_argument("-p", "--prefix", type=str,
                     help="List all the prefixes for a given country")
  opts = parser.parse_args()

  try:
    if opts.list:
      clist()
    elif opts.country:
      country(opts.country)
    elif opts.check:
      check(opts.check)
    elif opts.prefix:
      get_prefix(opts.prefix)
  except KeyError as err:
    print(f"Error: {err}", file=sys.stderr)
    sys.exit(os.EX_DATAERR)

if __name__ == "__main__":
  main()
