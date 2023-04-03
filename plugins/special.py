#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

from datetime import datetime, timedelta

from dbutils import connect_db
from .base import CallSelector

class DXCC100(CallSelector):

  WORKED = "SELECT country FROM cqcalls WHERE status = 2 GROUP BY country HAVING count(*) >= ?"

  def __init__(self):
    super().__init__()
    self.worked_count = getattr(self.config, "worked_count", 2)

  def get(self):
    records = []

    with connect_db(self.db_name) as conn:
      curs = conn.cursor()
      result = curs.execute(self.WORKED, (self.worked_count,))
      worked = set([r['country'] for r in result])

    for record in super().get():
      self.log.debug("%s %s %s (%s)", record['call'], record['country'], record['snr'])
      if record['country'] not in worked:
        self.log.debug('Selected: %s', record['call'])
        records.append(record)

    return self.get_record(records)


class POTA(CallSelector):

  def __init__(self):
    super().__init__()

  def get(self):
    records = []
    for record in super().get():
      if record['extra'] and record['extra'].upper() == 'POTA':
        records.append(record)
    return self.get_record(records)
