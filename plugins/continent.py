#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

import operator

from datetime import datetime, timedelta

from dbutils import connect_db
from .base import CallSelector

class LandBase(CallSelector):

  REQ = 'select 1'

  def __init__(self):
    super().__init__()
    c_list = self.config.list
    if isinstance(c_list, str):
      c_list = [c_list]
    c_list = (f'"{c}"' for c in c_list)
    if hasattr(self.config, 'Reverse') and self.config.Reverse:
      _not = 'NOT'
    else:
      _not = ''

    self.req = self.REQ.format(_not, ','.join(c_list))
    self.conn = connect_db(self.db_name)

  def get(self):
    records = []
    start = datetime.utcnow() - timedelta(seconds=self.delta)
    with connect_db(self.db_name) as conn:
      curs = conn.cursor()
      curs.execute(self.req, (start,))
      for record in (dict(r) for r in curs):
        record['coef'] = self.coefficient(record['distance'], record['snr'])
        records.append(record)
    records.sort(key=operator.itemgetter('coef'), reverse=True)
    return records[0] if records else None


class Continent(LandBase):

  REQ = """
  SELECT call, snr, distance, time FROM cqcalls
  WHERE status = 0 AND time > ? AND continent {} in ({})
  """

class Country(LandBase):

  REQ = """
  SELECT call, snr, distance, time FROM cqcalls
  WHERE status = 0 AND time > ? AND country {} in ({})
  """
