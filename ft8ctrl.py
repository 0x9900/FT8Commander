#!/usr/bin/env python
#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#
import logging
import os
import random
import re
import select
import socket
import sys
import time

from argparse import ArgumentParser
from datetime import datetime
from importlib import import_module
from logging.handlers import RotatingFileHandler
from queue import Queue

import geo
import wsjtx

from dbutils import DBCommand
from dbutils import create_db, DBInsert, Purge, get_band
from plugins.base import LOTW

from config import Config

SEQUENCE_TIME = {
  'FT8':  (2, 17, 32, 47),
  'FT4': (1, 7, 13, 19, 25, 31, 37, 43, 49, 55),
}

PARSERS = {
  'REPLY': re.compile(r'^((?!CQ)(?P<to>\w+)(|/\w+)) (?P<call>\w+)(|/\w+) .*'),
  'CQ': re.compile(r'^CQ\s(?:CQ\s|(?P<extra>[\S.]+)\s|)(?P<call>\w+(|/\w+))\s(?P<grid>[A-Z]{2}[0-9]{2})'),
  'BROKENCQ': re.compile(r'^CQ\s(?P<call>\w+(|/\w+))$'),
}

LOGFILE_SIZE = 8<<16
LOGFILE_NAME = 'ft8ctrl.log'
LOG = logging.getLogger()

class Sequencer:
  def __init__(self, config, queue, call_select):
    self.db_name = config.db_name
    self.mycall = config.my_call
    self.queue = queue
    self.selector = call_select
    self.follow_frequency = config.follow_frequency

    bind_addr = socket.gethostbyname(config.wsjt_ip)
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.sock.setblocking(False) # Set socket to non-blocking mode
    self.sock.bind((bind_addr, config.wsjt_port))

    self.logger_ip = getattr(config, 'logger_ip', None)
    self.logger_port = getattr(config, 'logger_port', None)
    self.logger_socket = None

  def call_station(self, ip_from, data):
    LOG.info(('Calling: %s (%s), From: %s, SNR: %d, Distance: %d, Band: %dm '
             '- %s - https://www.qrz.com/db/%s'),
             data['call'], data['extra'], data['country'], data['snr'], data['distance'],
             data['band'], data['selector'], data['call'])
    pkt = data['packet']
    packet = wsjtx.WSReply()
    packet.call = data['call']
    packet.Time = data['time']
    packet.SNR = data['snr']
    packet.DeltaTime = pkt['DeltaTime']
    packet.DeltaFrequency = pkt['DeltaFrequency']
    packet.Mode = pkt['Mode']
    packet.Message = pkt['Message']
    if self.follow_frequency:
      packet.Modifiers = wsjtx.Modifiers.SHIFT

    LOG.debug('Transmitting %s', packet)
    self.sock.sendto(packet.raw(), ip_from)

  def stop_transmit(self, ip_from):
    stop_pkt = wsjtx.WSHaltTx()
    stop_pkt.tx = True
    try:
      self.sock.sendto(stop_pkt.raw(), ip_from)
    except socket.error as err:
      LOG.error(err)

  def sendto_log(self, packet):
    if not self.logger_ip or not self.logger_port:
      return
    packet.TXPower = random.randint(11, 17)
    packet.Comments = "[ft8ctrl] " +  packet.Comments
    if not self.logger_socket:
      self.logger_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.logger_socket.sendto(packet.raw(), (self.logger_ip, self.logger_port))

  def parser(self, message):
    for name, regexp in PARSERS.items():
      match = regexp.match(message)
      if not match:
        continue
      data = match.groupdict()
      if name == 'BROKENCQ':
        name = 'CQ'
        data['extra'] = data['grid'] = None
      if name == 'CQ':
        LOG.debug("%s = %r, %s", name, data, message)
      return (name, data)
    LOG.debug('Unmatched: %s', message)
    return (None, None)

  def logcall(self, packet):
    self.sendto_log(packet)
    frequency = packet.DialFrequency
    self.queue.put(
      (DBCommand.STATUS, {"call": packet.DXCall, "status": 2, "band": get_band(frequency)})
    )
    LOG.info("** Logged call: %s, Grid: %s, Mode: %s",
             packet.DXCall, packet.DXGrid, wsjtx.Mode(packet.Mode).name)

  def decode(self, packet):
    try:
      return self.parser(packet.Message)
    except TypeError as err:
      LOG.error('Error: %s - Message: %s', err, packet.Message)
    return (None, None)


  def run(self):
    ip_from = None
    tx_status = False
    frequency = 0
    pause = False
    current = None
    sequence = []

    while True:
      fds, _, _ = select.select([self.sock, sys.stdin], [], [], .7)
      for fdin in fds:
        if fdin == sys.stdin:
          line = fdin.readline().strip().upper()
          if not line:
            continue
          if line == 'QUIT':
            return

          if "HELP" in line or "?" in line:
            LOG.info('The commands are: QUIT, CACHE, PAUSE, RUN, SELECTOR or HELP')
          elif line == 'PAUSE':
            LOG.warning('Paused...')
            pause = True
          elif line == 'RUN':
            LOG.warning('Run...')
            pause = False
          elif line in ("SELECTOR", "SELECTORS"):
            selector_list = [s.__class__.__name__ for s in self.selector.call_select]
            LOG.warning('Selectors: %s', ', '.join(selector_list))
          elif line == 'CACHE':
            LOG.info("Cache LOTW: %s", LOTW.__contains__.cache_info())
            LOG.info("Cache grid2latlon: %s", geo.grid2latlon.cache_info())
          else:
            LOG.warning('Unknown command: %s', line)
          continue

        rawdata, ip_from = fdin.recvfrom(1024)
        packet = wsjtx.ft8_decode(rawdata)
        if isinstance(packet, wsjtx.WSHeartbeat):
          pass
        elif isinstance(packet, wsjtx.WSLogged):
          self.logcall(packet)
          current = None
        elif isinstance(packet, wsjtx.WSDecode):
          name, match = self.decode(packet)
          if name == 'REPLY' and match['call'] == current and match['to'] != self.mycall:
            LOG.info("Stop Transmit: %s Replying to %s ", match['call'], match['to'])
            self.stop_transmit(ip_from)
            self.queue.put((DBCommand.DELETE, {"call": match['call'], "band": get_band(frequency)}))
          elif name == 'CQ':
            match['frequency'] = frequency
            match['band'] = get_band(frequency)
            match['packet'] = packet.as_dict()
            self.queue.put((DBCommand.INSERT, match))
          continue
        elif isinstance(packet, wsjtx.WSStatus):
          sequence = SEQUENCE_TIME[packet.TXMode]
          frequency = packet.Frequency
          tx_status = any([packet.Transmitting, packet.TXEnabled])
          if (packet.Transmitting and packet.DXCall):
            self.queue.put(
              (DBCommand.STATUS, {"call": packet.DXCall, "status": 1, "band": get_band(frequency)})
            )
          LOG.debug("%s => TX: %s, TXEnabled: %s - TXWatchdog: %s", packet.DXCall,
                   packet.Transmitting, packet.TXEnabled, packet.TXWatchdog)

      ## Outside the for loop ##
      if not pause and not tx_status:
        _now = datetime.utcnow()
        if _now.second in sequence:
          data = self.selector(get_band(frequency))
          if data:
            self.call_station(ip_from, data)
            current = data['call']
          else:
            current = None
          time.sleep(1)


class LoadPlugins:

  def __init__(self, plugins):
    """Load and initialize plugins"""
    self.call_select = []
    if isinstance(plugins, str):
      plugins = [plugins]

    for plugin in plugins:
      *module_name, class_name = plugin.split('.')
      module_name = '.'.join(['plugins'] + module_name)
      module = import_module(module_name)
      klass = getattr(module, class_name)
      self.call_select.append(klass())

  def __call__(self, band):
    for selector in self.call_select:
      data = selector.get(band)
      if not data:
        continue
      data['selector'] = selector.__class__.__name__
      LOG.debug('Select: %s, From: %s, SNR: %d, Distance: %dKm, Band: %dm, Selector: %s',
                data['call'], data['country'], data['snr'], data['distance'],
                data['band'], data['selector'])
      return data
    return None

  def __repr__(self):
    return '<LoadPlugins> ' + ', '.join(p.__class__.__name__ for p in self.call_select)


def main():
  global LOG
  logging.basicConfig(
    format='%(asctime)s - %(levelname)-7s %(lineno)3d:%(module)-8s - %(message)s',
    datefmt='%H:%M:%S', level=logging.INFO,
    handlers=[
      RotatingFileHandler(LOGFILE_NAME, maxBytes=LOGFILE_SIZE, backupCount=5),
      logging.StreamHandler()
    ]
  )
  loglevel = os.getenv('LOG_LEVEL', 'INFO').upper()
  if loglevel not in logging._nameToLevel: # pylint: disable=protected-access
    logging.error('Log level "%s" does not exist, defaulting to INFO', loglevel)
    loglevel = logging.INFO
  logging.root.setLevel(loglevel)
  LOG = logging.getLogger('FT8Ctrl')

  parser = ArgumentParser(description="ft8ctl wsjt-x automation")
  parser.add_argument("-c", "--config", help="Name of the configuration file")
  opts = parser.parse_args()

  config = Config(opts.config)
  config = config['ft8ctrl']
  create_db(config.db_name)

  queue = Queue()
  db_thread = DBInsert(config, queue)
  db_thread.daemon = True
  db_thread.start()

  db_purge = Purge(config.db_name, config.retry_time)
  db_purge.daemon = True
  db_purge.start()

  LOG.info('Call selector: %s', ', '.join(config.call_selector))
  call_select = LoadPlugins(config.call_selector)
  main_loop = Sequencer(config, queue, call_select)
  try:
    main_loop.run()
  except KeyboardInterrupt:
    LOG.info('^C pressed exiting')

if __name__ == '__main__':
  main()
