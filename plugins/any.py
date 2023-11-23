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
    self.log.info('My continent %s', self.continent)

  def get(self, band):
    records = []
    for record in super().get(band):
      if all([record['extra'] == 'DX', record['continent'] == self.continent]):
        self.log.info("Ignore %s %s %s", record['call'], record['continent'], record['extra'])
        continue
      records.append(record)
    return self.select_record(records)
