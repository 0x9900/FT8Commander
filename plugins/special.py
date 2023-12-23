#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

from dbutils import connect_db

from .base import CallSelector


class DXCC100(CallSelector):

  WORKED = ("SELECT country FROM cqcalls WHERE status = 2 and band = ? "
            "GROUP BY country HAVING count(*) >= ?")

  def __init__(self):
    super().__init__()
    self.worked_count = getattr(self.config, "worked_count", 2)

  def get(self, band):
    records = []
    with connect_db(self.db_name) as conn:
      curs = conn.cursor()
      result = curs.execute(self.WORKED, (band, self.worked_count,))
      worked = set(r['country'] for r in result)

    for record in super().get(band):
      # self.log.debug("%s %s %s (%s)", record['call'], record['country'], record['snr'], band)
      if record['country'] not in worked:
        self.log.debug('Selected: %s', record['call'])
        records.append(record)

    return self.select_record(records)


class Extra(CallSelector):

  def __init__(self):
    super().__init__()
    self.reverse = getattr(self.config, 'reverse', False)
    self.ex_list = set(getattr(self.config, 'list', []))

  def get(self, band):
    records = []
    for record in super().get(band):
      if (record['extra'] in self.ex_list) ^ self.reverse:
        records.append(record)
    return self.select_record(records)
