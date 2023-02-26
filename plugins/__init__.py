#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

import logging

from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from ..config import Config

class CallSelector(ABC):

  def __init__(self):
    config = Config()
    self.config = config.get(self.__class__.__name__)
    self.db_name = config['ft8ctrl.db_name']
    self.log = logging.getLogger(self.__class__.__name__)
    try:
      self.delta = self.config.delta
    except AttributeError:
      self.delta = 20

  @abstractmethod
  def get(self):
    pass

  @staticmethod
  def coefficient(dist, snr):
    return dist * 10**(snr/10)
