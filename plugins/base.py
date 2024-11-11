#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

import dbm
import logging
import marshal
import operator
import os
import ssl
import time
import warnings
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from functools import lru_cache, update_wrapper
from pathlib import Path
from urllib import request

from config import Config
from dbutils import connect_db

# Silence Python 3.12 deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

LOTW_URL = 'https://lotw.arrl.org/lotw-user-activity.csv'
LOTW_CACHE = Path('/tmp/lotw_cache.dat')
LOTW_EXPIRE = 7 * 86400
LOTW_LASTSEEN = 270             # Users who haven't used LOTW for 'n' days

MIN_SNR = -50
MAX_SNR = +50

ZERO = marshal.dumps(0)


class SingleObjectCache():
  __slots__ = ['_data', '_age', 'maxage']

  def __init__(self, maxage=3):
    self.maxage = maxage
    self._data = []
    self._age = 0

  def __call__(self, func):
    def wrapper(*args, **kwargs):
      now = time.time()
      if self._age + self.maxage < now:
        self._data = func(*args, **kwargs)
        self._age = now
      return self._data
    return update_wrapper(wrapper, func)

  def __repr__(self):
    return "<SingleObjectCache> {self.maxage}"


class BlackList:
  # Singleton class

  def __new__(cls):
    if hasattr(cls, '_instance') and isinstance(cls._instance, cls):
      return cls._instance

    cls.blacklist = []
    cls._instance = super(BlackList, cls).__new__(cls)
    cls.log = logging.getLogger(f'ft8ctrl.{cls.__name__}')
    config = Config()
    try:
      cls.blacklist = [c.upper() for c in config.get('BlackList', [])]
    except KeyError:
      pass

    try:
      tsize = os.get_terminal_size()
      width = tsize.columns - 50
    except OSError:
      width = 70
    _bl = ', '.join(c for c in cls.blacklist)[:width]
    _bl = _bl[:_bl.rindex(',')]
    cls.log.info("BlackList: %s...", _bl)

    return cls._instance

  def check(self, call):
    call = call.upper()
    if call in self.blacklist:
      return True
    return False

  def __contains__(self, call):
    return self.check(call)


class CallSelector(ABC):
  # pylint: disable=too-many-instance-attributes

  REQ = ("SELECT * FROM cqcalls WHERE "
         "status = 0 AND band = ? AND time > ?")

  def __init__(self):
    config = Config()
    self.config = config.get(self.__class__.__name__)
    self.log = logging.getLogger(f'ft8ctrl.{self.__class__.__name__}')

    self.debug = getattr(self.config, "debug", False)
    if self.debug:
      self.log.setLevel(logging.DEBUG)

    self.blacklist = BlackList()
    self.db_name = Path(config['ft8ctrl.db_name']).expanduser()
    self.min_snr = getattr(self.config, "min_snr", MIN_SNR)
    self.max_snr = getattr(self.config, "max_snr", MAX_SNR)
    self.delta = getattr(self.config, "delta", 29)
    self.continent = getattr(self.config, 'my_continent', 'NA')
    self.log.debug('My continent %s', self.continent)

    if getattr(self.config, "lotw_users_only", False):
      self.lotw = LOTW()
      self.log.info('%s reply to LOTW users only', self.__class__.__name__)
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
      curs.execute(self.REQ, (band, start))
      for record in (dict(r) for r in curs):
        if record['extra'] == 'DX' and record['continent'] == self.continent:
          self.log.warning("Ignore %s %s calling %s",
                           record['call'], record['continent'],
                           record['extra'])
        else:
          record['coef'] = self.coefficient(record['distance'], record['snr'])
          records.append(record)
    return records

  def select_record(self, records):
    records = self.sort(records)
    for record in records:
      if not self.min_snr < record['snr'] < self.max_snr:
        continue
      if record['call'] in self.blacklist:
        self.log.debug('%s is blacklisted', record['call'])
        continue
      if record['call'] not in self.lotw:
        self.log.debug('%s is not an lotw user', record['call'])
        continue
      return record
    return None

  @staticmethod
  def coefficient(dist, snr):
    return dist * 10**(snr / 10)

  @staticmethod
  def sort(records):
    return sorted(records, key=operator.itemgetter('snr'), reverse=True)


class Nothing:
  # pylint: disable=too-few-public-methods
  def __contains__(self, call):
    return True


class LOTW:
  # Singleton class

  def __new__(cls):
    if hasattr(cls, '_instance') and isinstance(cls._instance, cls):
      return cls._instance

    cls.log = logging.getLogger(f'ft8ctrl.{cls.__name__}')
    cls.log.info('LOTW database: %s (%d days)', LOTW_CACHE, LOTW_LASTSEEN)

    if not LOTW_CACHE.parent.exists():
      LOTW_CACHE.parent.mkdir(parents=True)

    try:
      with dbm.open(str(LOTW_CACHE), 'r') as fdb:
        age = marshal.loads(fdb.get('__age__', ZERO))
    except dbm.error:
      age = 0

    if time.time() > age + LOTW_EXPIRE:
      cls.log.info('LOTW cache expired. Reload...')
      context = ssl._create_unverified_context()
      with request.urlopen(LOTW_URL, context=context) as response:
        if response.status != 200:
          raise SystemError('Download error') from None
        try:
          LOTW.store_lotw(response)
        except IOError as err:
          cls.log.error(err)

    cls.log.info('LOTW lookup database ready')
    cls.__contains__ = lru_cache(maxsize=512)(cls.__contains__)

    cls._instance = super(LOTW, cls).__new__(cls)
    return cls._instance

  @staticmethod
  def store_lotw(response):
    start_date = datetime.now() - timedelta(days=LOTW_LASTSEEN)
    charset = response.info().get_content_charset('utf-8')
    try:
      with dbm.open(str(LOTW_CACHE), 'c') as fdb:
        for line in (r.decode(charset) for r in response):
          fields = list(line.rstrip().split(','))
          if datetime.strptime(fields[1], '%Y-%m-%d') > start_date:
            fdb[fields[0].upper()] = marshal.dumps(fields[1])
        fdb['__age__'] = marshal.dumps(int(time.time()))
    except dbm.error as err:
      raise IOError from err

  def __contains__(self, key):
    try:
      with dbm.open(str(LOTW_CACHE), 'r') as fdb:
        return key.upper() in fdb
    except dbm.error as err:
      logging.error(err)
      raise SystemError(err) from None

  def __repr__(self):
    try:
      _st = os.stat(LOTW_CACHE)
      fdate = float(_st.st_mtime)
      expire = LOTW_EXPIRE - int(time.time() - fdate)
      if expire < 1:
        raise IOError
    except IOError:
      return f'<LOTW id:{id(self)}> LOTW cache "Expired"'

    return f"<LOTW id:{id(self)}> LOTW cache expire in: {expire} seconds"
