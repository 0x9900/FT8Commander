#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#
#

import operator
import re

from datetime import datetime, timedelta

from dbutils import connect_db
from .base import CallSelector

class Prefix(CallSelector):

  REQ = """
  SELECT call, snr, distance, time FROM cqcalls
  WHERE status = 0 AND time > ? AND call REGEXP ?
  """

  def __init__(self):
    super().__init__()
    self.conn = connect_db(self.db_name)
    self.conn.create_function('regexp', 2, Prefix.regexp)
    self.expr = self.config.regexp

  def get(self):
    records = []
    start = datetime.utcnow() - timedelta(seconds=self.delta)
    with self.conn:
      curs = self.conn.cursor()
      curs.execute(self.REQ, (start, self.expr))
      for record in (dict(r) for r in curs):
        record['coef'] = self.coefficient(record['distance'], record['snr'])
        records.append(record)
    records.sort(key=operator.itemgetter('coef'), reverse=True)
    return records[0] if records else None

  @staticmethod
  def regexp(expr, data):
    return 1 if re.search(expr, data) else 0
