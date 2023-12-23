#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime
from enum import Enum
from threading import Thread

import DXEntity

import geo


# DBInsert commands.
class DBCommand(Enum):
  INSERT = 1
  STATUS = 2
  DELETE = 3


SQL_TABLE = """
CREATE TABLE IF NOT EXISTS cqcalls
(
  call TEXT,
  extra TEXT,
  time TIMESTAMP,
  status INTEGER,
  snr INTEGER,
  grid TEXT,
  lat REAL,
  lon REAL,
  distance REAL,
  azimuth REAL,
  country TEXT,
  continent TEXT,
  cqzone INTEGER,
  ituzone INTEGER,
  frequency INTEGER,
  band INTEGER,
  packet JSON
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_call on cqcalls (call, band);
CREATE INDEX IF NOT EXISTS idx_time on cqcalls (time DESC);
CREATE INDEX IF NOT EXISTS idx_grid on cqcalls (grid ASC);
"""


logger = logging.getLogger('ft8ctrl.dbutils')


def get_band(key):
  _bands = {
    1: 160,
    3: 80,
    7: 40,
    10: 30,
    14: 20,
    18: 17,
    21: 15,
    24: 12,
    28: 10,
    50: 6,
  }

  key = int(key / 10**6)
  if key not in _bands:
    return 0
  return _bands[key]


class DBJSONEncoder(json.JSONEncoder):
  """Special JSON encoder capable of encoding sets"""
  def default(self, o):
    if isinstance(o, set):
      return {'__type__': 'set', 'value': list(o)}
    if isinstance(o, datetime):
      return {'__type__': 'datetime', 'value': o.timestamp()}

    return super().default(o)


class DBJSONDecoder(json.JSONDecoder):
  """Special JSON decoder capable of decoding sets encodes by IJSONEncoder"""
  def __init__(self):
    super().__init__(object_hook=self.dict_to_object)

  def dict_to_object(self, json_obj):
    if '__type__' not in json_obj:
      return json_obj
    if json_obj['__type__'] == 'set':
      return set(json_obj['value'])
    if json_obj['__type__'] == 'datetime':
      return datetime.fromtimestamp(json_obj['value'])

    return json_obj


sqlite3.register_adapter(dict, DBJSONEncoder().encode)
sqlite3.register_converter('JSON', lambda x: DBJSONDecoder().decode(x.decode('utf-8')))


def connect_db(db_name):
  try:
    conn = sqlite3.connect(db_name, timeout=15, detect_types=sqlite3.PARSE_DECLTYPES,
                           isolation_level=None)
    conn.row_factory = sqlite3.Row
  except sqlite3.OperationalError as err:
    logger.error("Database: %s - %s", db_name, err)
    sys.exit(os.EX_IOERR)
  return conn


def create_db(db_name):
  logger.info("Database: %s", db_name)
  with connect_db(db_name) as conn:
    curs = conn.cursor()
    curs.executescript(SQL_TABLE)


def get_call(db_name, call):
  req = "SELECT * FROM cqcalls WHERE call = ?"
  with connect_db(db_name) as conn:
    curs = conn.cursor()
    curs.execute(req, (call,))
    record = curs.fetchone()
  return dict(record) if record else {}


class DBInsert(Thread):

  INSERT = """
  INSERT INTO cqcalls VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  ON CONFLICT(call, band) DO UPDATE SET snr = excluded.snr, packet = excluded.packet
  WHERE status <> 2
  """
  UPDATE = "UPDATE cqcalls SET status=? WHERE status <> 2 and call = ? and band = ?"
  DELETE = "DELETE from cqcalls WHERE status= 1 AND call = ? and band = ?"

  def __init__(self, config, queue):
    super().__init__()
    self.db_name = config.db_name
    self.queue = queue
    self.origin = geo.grid2latlon(config.my_grid)
    self.dxe_lookup = DXEntity.DXCC(config.dxcc_path).lookup

  def run(self):
    # pylint: disable=no-member
    logger.info('Datebase Insert thread started')
    conn = connect_db(self.db_name)
    # Run forever and consume the queue
    while True:
      cmd, data = self.queue.get()
      if cmd == DBCommand.INSERT:
        lat, lon = geo.grid2latlon(data['grid'])
        data['lat'], data['lon'] = lat, lon
        data['distance'] = geo.distance(self.origin, (lat, lon))
        data['azimuth'] = geo.azimuth(self.origin, (lat, lon))
        try:
          dxentity = self.dxe_lookup(data['call'])
          data['country'] = dxentity.country
          data['continent'] = dxentity.continent
          data['cqzone'] = dxentity.cqzone
          data['ituzone'] = dxentity.ituzone
        except KeyError:
          logger.error('DXEntity for %s not found, this is probably a fake callsign', data['call'])
          continue
        try:
          DBInsert.write(conn, data)
        except sqlite3.OperationalError as err:
          logger.warning("Queue len: %d - Error: %s", self.queue.qsize(), err)
        except AttributeError as err:
          logger.error(err)
          logger.error(data)
      elif cmd == DBCommand.STATUS:
        try:
          DBInsert.status(conn, data)
        except sqlite3.OperationalError as err:
          logger.warning("Queue len: %d - Error: %s", self.queue.qsize(), err)
      elif cmd == DBCommand.DELETE:
        try:
          DBInsert.delete(conn, data)
        except sqlite3.OperationalError as err:
          logger.warning("Queue len: %d - Error: %s", self.queue.qsize(), err)

  @staticmethod
  def write(conn, call_info):
    # pylint: disable=no-member
    data = type('CallInfo', (object, ), call_info)
    with conn:
      curs = conn.cursor()
      curs.execute(DBInsert.INSERT, (
        data.call, data.extra, data.packet['Time'], 0, data.packet['SNR'], data.grid,
        data.lat, data.lon, data.distance, data.azimuth, data.country, data.continent,
        data.cqzone, data.ituzone, data.frequency, data.band, data.packet))
      if not curs.rowcount:
        logger.debug("DB Write: already worked %s on %d band", data.call, data.band)
      else:
        logger.debug("DB Write: %s, %s, %s, %s", data.call, data.continent, data.grid,
                     data.country)

  @staticmethod
  def status(conn, data):
    with conn:
      curs = conn.cursor()
      curs.execute(DBInsert.UPDATE, (data['status'], data['call'], data['band']))
      logger.debug("%s (%s, %s, %d)", DBInsert.UPDATE, data['status'], data['call'], data['band'])

  @staticmethod
  def delete(conn, data):
    with conn:
      curs = conn.cursor()
      curs.execute(DBInsert.DELETE, (data['call'], data['band']))
      logger.debug("%s (%s:%s)", DBInsert.DELETE, data['call'], data['band'])


class Purge(Thread):
  REQ = "DELETE FROM cqcalls WHERE status < 2 AND time < datetime('now','{} minute');"

  def __init__(self, db_name, purge_time):
    super().__init__()
    self.db_name = db_name
    self.purge_time = abs(purge_time) * -1  # make sure we have a negative number
    self.req = self.REQ.format(self.purge_time)
    logger.debug(self.req)

  def run(self):
    count = 0
    logger.info('Purge thread started (retry_time %d minutes)', abs(self.purge_time))
    conn = connect_db(self.db_name)
    while True:
      with conn:
        try:
          curs = conn.cursor()
          curs.execute(self.req)
          count = curs.rowcount
        except sqlite3.OperationalError as err:
          logger.error(err)
      logger.debug('Purge %d Records', count)
      time.sleep(60)
