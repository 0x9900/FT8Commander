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

  def get(self, band):
    records = []
    for record in super().get(band):
      records.append(record)
    return self.select_record(records)
