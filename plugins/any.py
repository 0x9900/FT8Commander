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

  def get(self):
    records = super().get()
    return self.select_record(records)
