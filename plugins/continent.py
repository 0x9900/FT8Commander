#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

from DXEntity import DXCC

from .base import CallSelector


class Continent(CallSelector):

  CONTINENTS = ["AF", "AS", "EU", "NA", "OC", "SA"]

  def __init__(self):
    super().__init__()
    self.c_list = set([])
    self.reverse = getattr(self.config, 'reverse', False)
    continents = getattr(self.config, 'list', [])
    continents = [continents] if isinstance(continents, str) else continents

    for cnt in continents:
      if cnt in self.CONTINENTS:
        self.c_list.add(cnt)
      else:
        self.log.warning('Ignoring continent: "%s" is not valid', cnt)

  def get(self, band):
    records = []
    for record in super().get(band):
      if (record['continent'] in self.c_list) ^ self.reverse:
        records.append(record)
    return self.select_record(records)


class Country(CallSelector):

  def __init__(self):
    super().__init__()
    dxcc = DXCC()
    self.c_list = set([])
    self.reverse = getattr(self.config, 'reverse', False)
    entities = getattr(self.config, 'list', [])
    entities = [self.config.list] if isinstance(entities, str) else self.config.list

    for country in entities:
      if dxcc.isentity(country):
        self.c_list.add(country)
      else:
        self.log.warning('Ignoring country: "%s" is not a valid entity', country)

  def get(self, band):
    records = []
    for record in super().get(band):
      if (record['country'] in self.c_list) ^ self.reverse:
        records.append(record)
    return self.select_record(records)
