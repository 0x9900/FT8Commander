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

def find(call):
  conn = connect_db('/tmp/auto_ft8.sql')
  conn.create_function('regexp', 2, regexp)
  with conn:
    curs = conn.cursor()
    curs.execute(REQ_RE, (call, ))
    for record in curs:
      yield record

def lookup(call):
  conn = connect_db('/tmp/auto_ft8.sql')
  with conn:
    curs = conn.cursor()
    curs.execute(REQ_LU, (call, ))
    yield curs.fetchone()

def delete_record(call):
  conn = connect_db('/tmp/auto_ft8.sql')
  with conn:
    curs = conn.cursor()
    curs.execute(REQ_DEL, (call,))

def main():
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
    records = find(call)
  else:
    records = lookup(call)

  for record in records:
    if not record:
      continue
    show_record(record)
    if opts.delete:
      delete_record(call)
      print(f'{call} Deleted')

if __name__ == "__main__":
  main()
