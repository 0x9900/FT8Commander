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

class ZoneBase(CallSelector):

  REQ = 'select 1'

  def __init__(self):
    super().__init__()
    zones_list = []
    cfg_list = self.config.list
    if isinstance(cfg_list, str):
      cfg_list = [cfg_list]

    if hasattr(self.config, 'Reverse') and self.config.Reverse:
      _not = 'NOT'
    else:
      _not = ''

    for zone in cfg_list:
      try:
        zones_list.append(str(int(zone)))
      except ValueError:
        self.log.warning('Zone "%s" is not a integer', zone)
    self.req = self.REQ.format(_not, ','.join(zones_list))
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


class CQZone(ZoneBase):

  REQ = """
  SELECT call, snr, distance, time FROM cqcalls
  WHERE status = 0 AND time > ? AND cqzone {} IN ({})
  """

class ITUZone(ZoneBase):

  REQ = """
  SELECT call, snr, distance, time FROM cqcalls
  WHERE status = 0 AND time > ? AND cqzone {} IN ({})
  """
