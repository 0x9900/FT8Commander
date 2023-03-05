#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

from datetime import datetime, timedelta

from dbutils import connect_db
from .base import CallSelector
from DXEntity import DXCC

class DXCC100(CallSelector):

  WORKED = "SELECT country FROM cqcalls WHERE status = 2 GROUP BY country HAVING count(*) > ?"

  REQ = """
  SELECT call, snr, distance, frequency, time, country FROM cqcalls
  WHERE status = 0 AND snr > ? AND time > ? and country not in ({})
  """

  def __init__(self):
    super().__init__()
    self.work_count = getattr(self.config, "work_count", 2)


  def get(self):
    records = []
    start = datetime.utcnow() - timedelta(seconds=self.delta)
    with connect_db(self.db_name) as conn:
      curs = conn.cursor()
      worked = curs.execute(self.WORKED, (self.work_count,))
      req = self.REQ.format(','.join(f"\"{c['country']}\"" for c in worked))
      curs.execute(req, (self.min_snr, start))
      for record in (dict(r) for r in curs):
        record['coef'] = self.coefficient(record['distance'], record['snr'])
        records.append(record)

    records = self.sort(records)
    return records[0] if records else None
