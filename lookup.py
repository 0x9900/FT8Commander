#!/usr/bin/env python
#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

from argparse import ArgumentParser
import re
import sys

from config import Config
from dbutils import connect_db

REQ_RE = '''
SELECT call, status, snr, grid, cqzone, ituzone, country, continent, time, frequency
FROM cqcalls WHERE call REGEXP ?
'''

REQ_LU = '''
SELECT call, status, snr, grid, cqzone, ituzone, country, continent, time, frequency
FROM cqcalls WHERE call = ?
'''

REQ_DEL = 'DELETE FROM cqcalls WHERE call = ?'

def regexp(expr, data):
  return 1 if re.search(expr, data) else 0

def show_record(rec):
  if not rec:
    return
  for key in rec.keys():
    print(f"{key.title():<10}: {rec[key]}")
  print('-' * 79)

def find(dbname, call):
  conn = connect_db(dbname)
  conn.create_function('regexp', 2, regexp)
  with conn:
    curs = conn.cursor()
    curs.execute(REQ_RE, (call, ))
    for record in curs:
      yield record

def lookup(dbname, call):
  conn = connect_db(dbname)
  with conn:
    curs = conn.cursor()
    curs.execute(REQ_LU, (call, ))
    yield curs.fetchone()

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
  config = Config()['ft8ctrl']
  parser = ArgumentParser(description="ft8ctl call sign status")
  x_group = parser.add_mutually_exclusive_group(required=False)
  x_group.add_argument("-p", "--partial", action="store_true", default=False,
                      help="When you only have a partial callsign")
  x_group.add_argument("-d", "--delete", action="store_true", default=False,
                      help="Reset the status")
  parser.add_argument('call', nargs=1, help="Call sign")

  opts = parser.parse_args()
  call = opts.call[0].upper()

  if opts.partial:
    records = find(config.db_name, call)
  else:
    records = lookup(config.db_name, call)

  for record in records:
    if not record:
      continue
    show_record(record)
  if opts.delete:
    delete_record(config.db_name, call)

if __name__ == "__main__":
  main()
