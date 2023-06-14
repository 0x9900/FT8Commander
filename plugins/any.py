#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

from .base import CallSelector

class Any(CallSelector):

  def get(self, band):
    records = super().get(band)
    return self.select_record(records)
