#!/usr/bin/env python
#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

import re
import sys


from dbutils import connect_db

REQ = '''
SELECT call, status, grid, cqzone, ituzone, country, continent, time
FROM cqcalls WHERE call REGEXP ?
'''


if len(sys.argv) != 2:
  print('Usage: lookup callsign')
  sys.exit(1)
else:
  call = sys.argv[1].upper()

def regexp(expr, data):
  return 1 if re.search(expr, data) else 0

def show_record(rec):
  for key in rec.keys():
    print(f"{key.title():<10}: {rec[key]}")

conn = connect_db('/tmp/auto_ft8.sql')
conn.create_function('regexp', 2, regexp)
with conn:
  curs = conn.cursor()
  curs.execute(REQ, (call, ))
  for record in curs:
    show_record(record)
