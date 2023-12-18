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
    self.call_list = getattr(self.config, 'list', [])
    self.reverse = getattr(self.config, 'reverse', False)

  def get(self, band):
    records = []
    for record in super().get(band):
      if bool(record['call'] in self.call_list) ^ self.reverse:
        self.log.warning('Select call %s from list', record['call'])
        records.append(record)
      elif bool(self.expr.search(record['call'])) ^ self.reverse:
        self.log.warning('Select call %s from regexp', record['call'])
        records.append(record)

    return self.select_record(records)
