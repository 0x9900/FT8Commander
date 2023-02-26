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
from threading import Thread

import DXEntity
import geo

# DBInsert commands.
INSERT = 1
STATUS = 2

LOG = logging.getLogger('dbutil')

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
  packet JSON
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_call on cqcalls (call);
CREATE INDEX IF NOT EXISTS idx_time on cqcalls (time DESC);
CREATE INDEX IF NOT EXISTS idx_grid on cqcalls (grid ASC);
"""

class DBJSONEncoder(json.JSONEncoder):
  """Special JSON encoder capable of encoding sets"""
  def default(self, obj):
    if isinstance(obj, set):
      return {'__type__': 'set', 'value': list(obj)}
    if isinstance(obj, datetime):
      return {'__type__': 'datetime', 'value': obj.timestamp()}

    return super(IJSONEncoder, self).default(obj)

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
    logging.error("Database: %s - %s", db_name, err)
    sys.exit(os.EX_IOERR)
  return conn


def create_db(db_name):
  logging.info("Database: %s", db_name)
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

  def __init__(self, db_name, queue):
    super().__init__()
    self.db_name = db_name
    self.queue = queue
    self.origin = geo.grid2latlon('CM87vl')
    self.dxe_lookup = DXEntity.DXCC().lookup

  def run(self):
    LOG.info('Datebase Insert thread started')
    conn = connect_db(self.db_name)
    # Run forever and consume the queue
    while True:
      cmd, data = self.queue.get()
      if cmd == INSERT:
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
          data['country'] = data['continent'] = None

        LOG.debug("DB Write: %s (%4d, %4d) %s", data['call'], lat, lon, data['country'])
        try:
          DBInsert.write(conn, data)
        except sqlite3.OperationalError as err:
          LOG.warning("Queue len: %d - Error: %s", self.queue.qsize(), err)
      elif cmd == STATUS:
        try:
          DBInsert.status(conn, data)
        except sqlite3.OperationalError as err:
          LOG.warning("Queue len: %d - Error: %s", self.queue.qsize(), err)

  @staticmethod
  def write(conn, call_info):
    data = type('CallInfo', (object, ), call_info)

    with conn:
      curs = conn.cursor()
      curs.execute("""INSERT INTO cqcalls VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(call) DO UPDATE SET snr=?, time=?, packet=?""", (
        data.call, data.extra, data.packet['Time'], 0, data.packet['SNR'], data.grid,
        data.lat, data.lon, data.distance, data.azimuth, data.country, data.continent,
        data.cqzone, data.ituzone, data.frequency, data.packet,
        data.packet['SNR'], data.packet['Time'], data.packet))

  @staticmethod
  def status(conn, call):
    with conn:
      curs = conn.cursor()
      curs.execute('UPDATE cqcalls SET status=? WHERE call=?', (call['status'], call['call']))


class Purge(Thread):
  REQ = "DELETE FROM cqcalls WHERE status < 2 AND time < datetime('now','{} minute');"

  def __init__(self, db_name, purge_time):
    super().__init__()
    self.db_name = db_name
    self.purge_time = abs(purge_time) * -1 # make sure we have a negative number
    self.req = self.REQ.format(self.purge_time)
    LOG.debug(self.req)

  def run(self):
    count = 0
    LOG.info('Purge thread started (purge_time %d)', self.purge_time)
    conn = connect_db(self.db_name)
    while True:
      with conn:
        try:
          curs = conn.cursor()
          curs.execute(self.req)
          count = curs.rowcount
        except sqlite3.OperationalError as err:
          LOG.error(err)
      LOG.info('Purge %d Records', count)
      time.sleep(60)
