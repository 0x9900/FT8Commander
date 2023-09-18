#!/usr/bin/env python
#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

import os
import re
import sqlite3
import sys
import time

from argparse import ArgumentParser, ArgumentError
from datetime import datetime, timedelta

import tabulate

from config import Config
from dbutils import connect_db
from plugins.base import LOTW

KEYS = ['call', 'status', 'band', 'snr', 'grid', 'cqzone', 'ituzone', 'country', 'continent',
        'time', 'extra']

REQ_DEL = 'DELETE FROM cqcalls WHERE call = ? AND band = ?'

def dict_factory(cursor, row):
  data = {}
  for idx, col in enumerate(cursor.description):
    data[col[0]] = row[idx]
  return data

def dict_factory(cursor, row):
  data = {}
  for idx, col in enumerate(cursor.description):
    data[col[0]] = row[idx]
  return data

def regexp(expr, data):
  return 1 if re.search(expr, data) else 0

def find(dbname, what, var, band=None):
  reqs = {
    'call': 'WHERE call REGEXP ?',
    'status': 'WHERE status = ?',
    'country': 'WHERE country = ?',
  }
  req = [f'SELECT {", ".join(KEYS)} FROM cqcalls']
  req.append(reqs[what])
  req.append('AND band = ?' if band else ' AND NULL is ?')
  req.append(' ORDER BY time ASC')

  lotw = LOTW()
  conn = connect_db(dbname)
  conn.row_factory = dict_factory
  if what == 'call':
    conn.create_function('regexp', 2, regexp)

  try:
    with conn:
      curs = conn.cursor()
      curs.execute(' '.join(req), (var, band))
      for record in curs:
        record['lotw'] = record['call'] in lotw
        yield record
  except sqlite3.OperationalError as err:
    raise SystemError(err)

def delete_record(dbname, call, band):
  call = call.upper()
  conn = connect_db(dbname)
  with conn:
    curs = conn.cursor()
    curs.execute(REQ_DEL, (call, band))
  action = 'Deleted' if curs.rowcount > 0 else 'Not found'
  print(f'{call} on {band}m band - {action}')

def run(dbname, delta=30):
  lotw = LOTW()
  req = f'SELECT {",".join(KEYS)} FROM cqcalls WHERE time > ?'
  conn = connect_db(dbname)
  conn.row_factory = dict_factory

  def fetch():
    start = datetime.utcnow() - timedelta(seconds=delta)
    with conn:
      curs = conn.cursor()
      curs.execute(req, (start, ))
      records = []
      for record in curs:
        record['lotw'] = record['call'] in lotw
        records.append(record)
      return records

  while True:
    records = fetch()
    if records:
      clear()
      print(tabulate.tabulate(fetch(), headers='keys'))
      print()
    time.sleep(15)

def clear():
  if os.name == 'posix':
    print("\033[H\033[2J")

def type_call(parg):
  return parg.upper()

def main():
  parser = ArgumentParser(description="ft8ctl call sign status")
  parser.add_argument("-C", "--config", help="Name of the configuration file")
  exgroup = parser.add_mutually_exclusive_group(required=True)
  exgroup.add_argument("-d", "--delete", type=type_call, help="Delete entry args are call band")
  exgroup.add_argument("-r", "--run", type=int, help="Show the last seconds entries")
  exgroup.add_argument('-c', '--call', type=type_call, help="Call sign")
  exgroup.add_argument('--country', help="Country")
  exgroup.add_argument('--status', help="Status")
  parser.add_argument('-b', '--band', type=int)
  opts = parser.parse_args()

  config = Config(opts.config)
  config = config['ft8ctrl']
  records = []

  if opts.run:
    run(config.db_name, opts.run)
  elif opts.delete:
    if not opts.band:
      print('Argument --band is missing')
      return os.EX_USAGE
    delete_record(config.db_name, opts.delete, opts.band)
  elif opts.call:
    records = find(config.db_name, 'call', opts.call, opts.band)
  elif opts.country:
    records = find(config.db_name, 'country', opts.country, opts.band)
  elif opts.status:
    records = find(config.db_name, 'status', opts.status, opts.band)

  if records:
    print(tabulate.tabulate(records, headers='keys'))
  return os.EX_OK


if __name__ == "__main__":
  try:
    sys.exit(main())
  except KeyboardInterrupt:
    sys.exit(os.EX_OK)
