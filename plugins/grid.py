#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#
#

import re

from .base import CallSelector

class Grid(CallSelector):

  def __init__(self):
    super().__init__()
    self.expr = re.compile(self.config.regexp)
    self.reverse = getattr(self.config, 'reverse', False)

  def get(self, band):
    records = []
    for record in super().get(band):
      try:
        if bool(self.expr.search(record['grid'])) ^ self.reverse:
          records.append(record)
      except TypeError as err:
        self.log.warning('Unable to determine the grid: %s', record['packet']['Message'])
    return self.select_record(records)
