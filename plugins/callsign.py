#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#
#

import re

from .base import CallSelector

class CallSign(CallSelector):

  def __init__(self):
    super().__init__()
    self.expr = re.compile(self.config.regexp)
    self.reverse = getattr(self.config, 'reverse', False)

  def get(self, band):
    records = []
    for record in super().get(band):
      if bool(self.expr.search(record['call'])) ^ self.reverse:
        records.append(record)

    return self.select_record(records)
