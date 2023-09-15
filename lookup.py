#!/usr/bin/env python
#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

import re
import sqlite3
import sys
import time

from argparse import ArgumentParser
from datetime import datetime, timedelta

import tabulate

from config import Config
from dbutils import connect_db
from plugins.base import LOTW

KEYS = ['call', 'status', 'band', 'snr', 'grid', 'cqzone', 'ituzone', 'country', 'continent',
        'time', 'frequency', 'extra']
REQ = f'SELECT {",".join(KEYS)} FROM cqcalls WHERE call REGEXP ?'

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

def find(dbname, call):
  lotw = LOTW()
  conn = connect_db(dbname)
  conn.row_factory = dict_factory
  conn.create_function('regexp', 2, regexp)
  try:
    with conn:
      curs = conn.cursor()
      curs.execute(REQ, (call, ))
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
    if curs.rowcount > 0:
      print(f'Call: {call}, Band: {band} - Deleted')
    else:
      print(f'Call: {call}, Band: {band} - Not found')

def run(dbname):
  lotw = LOTW()
  delta = 30
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
    time.sleep(int(time.time()) % 5)
    records = fetch()
    if records:
      print(tabulate.tabulate(fetch(), headers='keys'))
      print()


def run(dbname):
  lotw = LOTW()
  delta = 30
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
    time.sleep(int(time.time()) % 5)
    records = fetch()
    if records:
      print(tabulate.tabulate(fetch(), headers='keys'))
      print()


def main():
  parser = ArgumentParser(description="ft8ctl call sign status")
  parser.add_argument("-C", "--config", help="Name of the configuration file")
  exgroup = parser.add_mutually_exclusive_group()
  exgroup.add_argument("-d", "--delete", nargs=2,
                       help="Delete entry args are call band")
  exgroup.add_argument("-r", "--run", action="store_true", default=False,
                       help="Show the last 15 seconds entries ")
  exgroup.add_argument('-c', '--call', help="Call sign")

  opts = parser.parse_args()

  config = Config(opts.config)
  config = config['ft8ctrl']

  if opts.run:
    run(config.db_name)
  elif opts.delete:
    records = find(config.db_name, f"^{opts.delete}$")
    print(tabulate.tabulate(records, headers='keys'))
    delete_record(config.db_name, *opts.delete)
  elif opts.call:
    call = opts.call.upper()
    try:
      records = find(config.db_name, call)
      print(tabulate.tabulate(records, headers='keys'))
    except SystemError as err:
      print(f'{err} - Call expression error')
      pass

if __name__ == "__main__":
  main()
