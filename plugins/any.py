#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

from .base import CallSelector

class Any(CallSelector):

  def __init__(self):
    super().__init__()
    self.continent = getattr(self.config, 'my_continent', 'NA')
    self.log.debug('My continent %s', self.continent)

  def get(self, band):
    records = []
    for record in super().get(band):
      if record['extra'] == 'DX' and record['continent'] == self.continent:
        self.log.debug("Ignore %s %s (%s)", record['call'], record['continent'], record['extra'])
      elif record['extra'] and record['extra'] != self.continent:
        self.log.debug("Ignore %s %s (%s)", record['call'], record['continent'], record['extra'])
      else:
        records.append(record)
    return self.select_record(records)
