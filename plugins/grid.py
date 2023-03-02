#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#
#

import re

from datetime import datetime, timedelta

from dbutils import connect_db
from .base import CallSelector

class Grid(CallSelector):

  REQ = """
  SELECT call, snr, distance, time FROM cqcalls
  WHERE status = 0 AND snr > ? AND time > ? AND grid ? REGEXP ?
  """

  def __init__(self):
    super().__init__()
    self.conn = connect_db(self.db_name)
    self.conn.create_function('regexp', 2, Grid.regexp)
    self.expr = self.config.regexp
    self.reverse = self.isreverse()

  def get(self):
    records = []
    start = datetime.utcnow() - timedelta(seconds=self.delta)
    with self.conn:
      curs = self.conn.cursor()
      curs.execute(self.REQ, (self.min_snr, start, self.reverse(), self.expr))
      for record in (dict(r) for r in curs):
        record['coef'] = self.coefficient(record['distance'], record['snr'])
        records.append(record)

    records = self.sort(records)
    return records[0] if records else None

  @staticmethod
  def regexp(expr, data):
    return 1 if re.search(expr, data) else 0
