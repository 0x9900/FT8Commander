#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

import dbm.gnu as gdbm
import logging
import operator
import os
import time

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from urllib import request

from config import Config

LOTW_URL = 'https://lotw.arrl.org/lotw-user-activity.csv'
LOTW_CACHE = '/tmp/lotw_cache.gdbm'
LOTW_EXPIRE = 10 # (7 * 86400)

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
    except (FileNotFoundError, EOFError):
      self.log.info('LOTW cache expired. Reload...')
      with request.urlopen(LOTW_URL) as response:
        if response.status != 200:
          raise SystemError('Download error')
        self.store_lotw(response)
    self.log.info('LOTW lookup database ready')

  def store_lotw(self, response):
    charset = response.info().get_content_charset('utf-8')
    try:
      with gdbm.open(LOTW_CACHE, 'c') as fdb:
        for line in (r.decode(charset) for r in response):
          fields = [f.strip() for f in line.split(',')]
          fdb[fields[0].upper()] = fields[1]
    except gdbm.error as err:
      self.log.error(err)
      raise IOError from err

  def __contains__(self, key):
    try:
      with gdbm.open(LOTW_CACHE, 'r') as fdb:
        return key in fdb
    except gdbm.error as err:
      logging.error(err)
      raise SystemError(err) from None

  def __repr__(self):
    try:
      st = os.stat(LOTW_CACHE)
      fdate = float(st.st_mtime)
      expire = LOTW_EXPIRE - int(time.time() - fdate)
      if expire < 1:
        raise IOError
    except IOError:
      return '<class LOTW> number of LOTW cache "Expired"'

    return f"<class LOTW> number of LOTW cache expire in: {expire} seconds"
