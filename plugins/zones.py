#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

from .base import CallSelector

class ZoneSelector(CallSelector):
  def __init__(self):
    super().__init__()
    self.reverse = getattr(self.config, 'reverse', False)
    zones_list = getattr(self.config, 'list', [])
    zones_list = [zones_list] if isinstance(zones_list, str) else zones_list
    self.z_list = set([])

    # Make sure zones are integers. Ignore the non integer values.
    for zone in zones_list:
      try:
        self.z_list.add(str(int(zone)))
      except ValueError:
        self.log.warning('%s "%s" is not a integer', self.__class__.__name__, zone)

  def get(self, band, field):
    records = []
    for record in super().get(band):
      if (record[field] in self.z_list) ^ self.reverse:
        records.append(record)
    return self.select_record(records)


class CQZone(ZoneSelector):
  def __init__(self):
    super().__init__()

  def get(sel, band):
    return super().get(band, 'cqzone')


class ITUZone(ZoneSelector):
  def __init__(self):
    super().__init__()

  def get(self, band):
    return super().get(band, 'ituzone')
