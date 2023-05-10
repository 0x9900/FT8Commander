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
from functools import update_wrapper
from urllib import request

from config import Config
from dbutils import connect_db

LOTW_URL = 'https://lotw.arrl.org/lotw-user-activity.csv'
LOTW_CACHE = '/tmp/lotw_cache.db'
LOTW_EXPIRE = (7 * 86400)

MIN_SNR = -50
MAX_SNR = +50

class SingleObjectCache():
  __slots__ = ['_data', '_age', 'maxage']

  def __init__(self, maxage=7):
    self.maxage = maxage
    self._data = None
    self._age = 0

  def __call__(self, func):
    def wrapper(*args, **kwargs):
      now = time.time()
      if self._age + self.maxage < now:
        self._data = func(*args, **kwargs)
        self._age = now
      return self._data
    return update_wrapper(wrapper, func)


class CallSelector(ABC):

  REQ = ("SELECT * FROM cqcalls WHERE "
         "status = 0 AND snr >= ? AND snr <= ? AND band = ? AND time > ?")

  def __init__(self):
    config = Config()
    self.config = config.get(self.__class__.__name__)
    self.db_name = config['ft8ctrl.db_name']
    self.min_snr = getattr(self.config, "min_snr", MIN_SNR)
    self.max_snr = getattr(self.config, "max_snr", MAX_SNR)
    self.delta = getattr(self.config, "delta", 29)
    self.debug = getattr(self.config, "debug", False)

    self.log = logging.getLogger(self.__class__.__name__)
    if self.debug:
      self.log.setLevel(logging.DEBUG)

    if getattr(self.config, "lotw_users_only", False):
      self.lotw = LOTW()
      self.log.info('Reply to LOTW users only')
    else:
      self.lotw = Nothing()

  @abstractmethod
  def get(self, band):
    return self._get(band)

  @SingleObjectCache()
  def _get(self, band):
    records = []
    start = datetime.utcnow() - timedelta(seconds=self.delta)
    with connect_db(self.db_name) as conn:
      curs = conn.cursor()
      curs.execute(self.REQ, (self.min_snr, self.max_snr, band, start))
      for record in (dict(r) for r in curs):
        record['coef'] = self.coefficient(record['distance'], record['snr'])
        records.append(record)
    return records

  def select_record(self, records):
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
    self.log.info('LOTW database: %s', LOTW_CACHE)

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
