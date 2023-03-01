#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

import io
import csv
import re
import logging

from copy import copy

from importlib.resources import files


class DXCCRecord:
  __slots__ = ['prefix', 'country', 'ctn', 'continent', 'cqzone',
               'ituzone', 'lat', 'lon', 'tz']

  def __init__(self, *args):
    for idx, field in enumerate(DXCCRecord.__slots__):
      if field == 'prefix':
        prefix, *_ = args[idx].lstrip('*').split('/')
        setattr(self, field, prefix)
      elif field in ('cqzone', 'ituzone'):
        setattr(self, field, int(args[idx]))
      elif field in ('lat', 'lon', 'tz'):
        setattr(self, field, float(args[idx]))
      else:
        setattr(self, field, args[idx])

  def __copy__(self):
    return type(self)(*[getattr(self, f) for f in DXCCRecord.__slots__])

  def __repr__(self):
    buffer = ', '.join([f"{f}: {getattr(self, f)}" for f in DXCCRecord.__slots__])
    return f"<DXCCRecord> {buffer}"


class DXCC:

  __parser = re.compile(r'(?:=|)(?P<prefix>\w+)(?:/\w+|)(?:\((?P<cqzone>\d+)\)|)'
                        r'(?:\[(?P<ituzone>\d+)\]|)(?:{(?P<continent>\w+)}|).*')
  def __init__(self):
    self._map = {}
    self._entities = set([])
    cty = files('bigcty').joinpath('cty.csv').read_text()
    logging.debug('Read bigcty callsign database')
    csvfd = csv.reader(io.StringIO(cty))
    for row in csvfd:
      self._map.update(self.parse(row))
    self.max_len = max(len(v) for v in self._map)
    for record in self._map.values():
      self._entities.add(record.country)

  @staticmethod
  def parse(record):
    dxmap = {}
    cty = DXCCRecord(*record[:9])
    dxmap[cty.prefix] = cty
    extra = record[9]
    for tag in extra.replace(';', '').split():
      match = DXCC.__parser.match(tag)
      if match:
        _cty = copy(cty)
        for key, val in match.groupdict().items():
          if not val:
            continue
          setattr(_cty, key, val)
          dxmap[_cty.prefix] = _cty
      else:
        logging.error('No match for %s', tag)

    return dxmap

  def lookup(self, call):
    call = call.upper()
    prefixes = {call[:c] for c in range(self.max_len, 0, -1)}
    for prefix in sorted(prefixes, reverse=True):
      if prefix in self._map:
        return self._map[prefix]
    raise KeyError(f"{call} not found")

  def isentity(self, country):
    if country in self._entities:
      return True
    return False

  @property
  def entities(self):
    return self._entities

  def __str__(self):
    return f"{self.__class__} {id(self)} ({len(self._map)} records)"

  def __repr__(self):
    return str(self)
