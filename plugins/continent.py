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

class LandBase(CallSelector):

  REQ = 'select 1'

  def __init__(self):
    super().__init__()

  def get(self):
    records = []
    start = datetime.utcnow() - timedelta(seconds=self.delta)
    with connect_db(self.db_name) as conn:
      curs = conn.cursor()
      curs.execute(self.req, (self.min_snr, self.max_snr, start))
      for record in (dict(r) for r in curs):
        record['coef'] = self.coefficient(record['distance'], record['snr'])
        records.append(record)

    return self.get_record(records)


class Continent(LandBase):

  REQ = """
  SELECT call, snr, distance, frequency, time, country FROM cqcalls
  WHERE status = 0 AND snr >= ? AND snr <= ? AND time > ? AND continent {} in ({})
  """

  CONTINENTS = ["AF", "AS", "EU", "NA", "OC", "SA"]

  def __init__(self):
    super().__init__()
    c_list = set([])
    continent = self.config.list
    if isinstance(continent, str):
      continent = [continent]
    for cnt in continent:
      if cnt not in self.CONTINENTS:
        self.log.warning('Ignoring continent: "%s" is not valid', cnt)
      else:
        c_list.add(f'"{cnt}"')

    self.req = self.REQ.format(self.isreverse(), ','.join(c_list))
    self.conn = connect_db(self.db_name)


class Country(LandBase):

  REQ = """
  SELECT call, snr, distance, frequency, time, country FROM cqcalls
  WHERE status = 0 AND snr >= ? AND snr <= ? AND time > ? AND country {} in ({})
  """

  def __init__(self):
    super().__init__()
    c_list = set([])
    dxcc = DXCC()
    entities = self.config.list
    if isinstance(entities, str):
      entities = [entities]

    for country in entities:
      if not dxcc.isentity(country):
        self.log.warning('Ignoring country: "%s" is not a valid entity', country)
      else:
        c_list.add(f'"{country}"')

    self.req = self.REQ.format(self.isreverse(), ','.join(c_list))
    self.conn = connect_db(self.db_name)
