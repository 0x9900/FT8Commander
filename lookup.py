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

from argparse import ArgumentParser

import tabulate

from config import Config
from dbutils import connect_db

KEYS = ['call', 'status', 'band', 'snr', 'grid', 'cqzone', 'ituzone', 'country', 'continent',
        'time', 'frequency', 'extra']
REQ = f'SELECT {",".join(KEYS)} FROM cqcalls WHERE call REGEXP ?'

REQ_DEL = 'DELETE FROM cqcalls WHERE call = ?'

def regexp(expr, data):
  return 1 if re.search(expr, data) else 0

def find(dbname, call):
  conn = connect_db(dbname)
  conn.create_function('regexp', 2, regexp)
  try:
    with conn:
      curs = conn.cursor()
      curs.execute(REQ, (call, ))
      for record in curs:
        yield record
  except sqlite3.OperationalError as err:
    raise SystemError(err)

def delete_record(dbname, call):
  conn = connect_db(dbname)
  with conn:
    curs = conn.cursor()
    curs.execute(REQ_DEL, (call,))
    if curs.rowcount > 0:
      print(f'{call} Deleted')
    else:
      print(f'{call} Not found')

def main():
  parser = ArgumentParser(description="ft8ctl call sign status")
  parser.add_argument("-c", "--config", help="Name of the configuration file")
  parser.add_argument("-d", "--delete", action="store_true", default=False,
                      help="Reset the status")
  parser.add_argument('call', nargs=1, help="Call sign")

  opts = parser.parse_args()
  call = opts.call[0].upper()

  config = Config(opts.config)
  config = config['ft8ctrl']

  if opts.delete:
    delete_record(config.db_name, call)
  else:
    try:
      records = find(config.db_name, call)
      table = records
      print(tabulate.tabulate(table, headers=[k.title() for k in KEYS]))
    except SystemError as err:
      print(f'{err} - Call expression error')
      pass

if __name__ == "__main__":
  main()
