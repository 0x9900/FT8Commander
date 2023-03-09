#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

import logging
import operator
import os
import pickle
import time

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from urllib import request

from config import Config

LOTW_URL = 'https://lotw.arrl.org/lotw-user-activity.csv'
LOTW_CACHE = '/tmp/lotw_cache.pkl'
LOTW_EXPIRE = (7 * 86400)

class CallSelector(ABC):

  def __init__(self):
    config = Config()
    self.config = config.get(self.__class__.__name__)
    self.db_name = config['ft8ctrl.db_name']
    self.log = logging.getLogger(self.__class__.__name__)
    self.min_snr = getattr(self.config, "min_snr", -50)
    self.delta = getattr(self.config, "delta", 28)

    self.lotw = Nothing()
    if getattr(self.config, "lotw_users_only", False):
      self.lotw = LOTW()


  @abstractmethod
  def get(self):
    pass

  def isreverse(self):
    if hasattr(self.config, 'reverse') and self.config.reverse:
      return 'NOT'
    return ''

  def get_record(self, records):
    records = self.sort(records)
    for record in records:
      self.log.debug('%s is not an lotw user', record['call'])
      if record['call'] in self.lotw:
        return record

    return None

  @staticmethod
  def coefficient(dist, snr):
    return dist * 10**(snr/10)

  @staticmethod
  def sort(records):
    return sorted(records, key=operator.itemgetter('snr'), reverse=True)


class Nothing:

  def __contains__(self, call):
    return True


class LOTW:

  def __init__(self):
    self._users = set([])
    self.log = logging.getLogger(self.__class__.__name__)

    try:
      st = os.stat(LOTW_CACHE)
      if time.time() > st.st_mtime + LOTW_EXPIRE:
        raise FileNotFoundError
      with open(LOTW_CACHE, 'rb') as lfd:
        self._users = pickle.load(lfd)
    except (FileNotFoundError, EOFError):
      self.log.info('LOTW cache expired. Reload...')
      with request.urlopen(LOTW_URL) as response:
        if response.status != 200:
          raise SystemError('Download error')
        charset = response.info().get_content_charset('utf-8')
        for line in (r.decode(charset) for r in response):
          fields = line.split(',')
          self._users.add(fields[0].strip())

      with open(LOTW_CACHE, 'wb') as lfd:
        pickle.dump(self._users, lfd)
    self.log.info('LOTW lookup database ready')

  def __contains__(self, call):
    _call = call.upper().strip()
    self.log.info('%s in LOTW: %s', _call, _call in self._users)
    return _call in self._users

  def __repr__(self):
    return f"<class LOTW> number of LOTW users: {len(self._users)}"
