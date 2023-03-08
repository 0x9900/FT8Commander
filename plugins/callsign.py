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

class CallSign(CallSelector):

  REQ = """
  SELECT call, snr, distance, frequency, time FROM cqcalls
  WHERE status = 0 AND snr > ? AND time > ? AND call {} REGEXP ?
  """

  def __init__(self):
    super().__init__()
    self.conn = connect_db(self.db_name)
    self.conn.create_function('regexp', 2, CallSign.regexp)
    self.expr = self.config.regexp
    self.req =  self.REQ.format(self.isreverse())

  def get(self):
    records = []
    start = datetime.utcnow() - timedelta(seconds=self.delta)
    with self.conn:
      curs = self.conn.cursor()
      curs.execute(self.req, (self.min_snr, start, self.expr))
      for record in (dict(r) for r in curs):
        record['coef'] = self.coefficient(record['distance'], record['snr'])
        records.append(record)

    return self.get_record(records)

  @staticmethod
  def regexp(expr, data):
    return 1 if re.search(expr, data) else 0
