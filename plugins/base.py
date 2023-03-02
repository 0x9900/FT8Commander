#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

import logging
import operator

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from config import Config

class CallSelector(ABC):

  def __init__(self):
    config = Config()
    self.config = config.get(self.__class__.__name__)
    self.db_name = config['ft8ctrl.db_name']
    self.log = logging.getLogger(self.__class__.__name__)
    self.min_snr = getattr(self.config, "min_snr", -50)
    self.delta = getattr(self.config, "delta", 28)


  @abstractmethod
  def get(self):
    pass

  def isreverse(self):
    if hasattr(self.config, 'reverse') and self.config.reverse:
      return 'NOT'
    return ''

  @staticmethod
  def coefficient(dist, snr):
    return dist * 10**(snr/10)

  @staticmethod
  def sort(records):
    return sorted(records, key=operator.itemgetter('snr'), reverse=True)
