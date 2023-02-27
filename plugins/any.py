#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

import operator

from datetime import datetime, timedelta

from . import CallSelector
from dbutils import connect_db

class Any(CallSelector):

  REQ = """
  SELECT call, snr, distance, time FROM cqcalls
  WHERE status = 0 AND time > ?
  """

  def get(self):
    records = []
    start = datetime.utcnow() - timedelta(seconds=self.delta)
    with connect_db(self.db_name) as conn:
      curs = conn.cursor()
      curs.execute(self.REQ, (start,))
      for record in (dict(r) for r in curs):
        record['coef'] = self.coefficient(record['distance'], record['snr'])
        records.append(record)
    records.sort(key=operator.itemgetter('coef'), reverse=True)
    return records[0] if records else None
