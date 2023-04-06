#!/usr/bin/env python
#
# BSD 3-Clause License
#
# Copyright (c) 2023, Fred W6BSD
# All rights reserved.
#

import logging
import os
import re
import select
import socket
import time
import sys

from argparse import ArgumentParser
from importlib import import_module
from queue import Queue

import wsjtx

from dbutils import create_db, DBInsert, Purge
from dbutils import DBCommand

from config import Config

PARSERS = {
  'REPLY': re.compile(r'^((?!CQ)(?P<to>\w+)(|/\w+)) (?P<call>\w+)(|/\w+) .*'),
  'CQ': re.compile(r'^CQ ((?P<extra>.*) |)(?P<call>\w+)(|/\w+) (?P<grid>[A-Z]{2}[0-9]{2})'),
}

LOG = logging.root

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

  def call_station(self, ip_from, data):
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
    except Exception as err:
      LOG.error(err)


  def parser(self, message):
    for name, regexp in PARSERS.items():
      match = regexp.match(message)
      if match:
        return (name, match.groupdict())
    return (None, None)

  def run(self):
    ip_from = None
    tx_status = False
    frequency = 0
    pause = False
    self.current = None

    while True:
      fds, _, _ = select.select([self.sock, sys.stdin], [], [], .5)
      sequence = int(time.time()) % 15
      for fdin in fds:
        if fdin == sys.stdin:
          line = fdin.readline().strip().upper()
          if not line:
            continue
          elif line == 'QUIT':
            return
          elif line == 'PAUSE':
            LOG.warning('Paused...')
            pause = True
          elif line == 'RUN':
            LOG.warning('Run...')
            pause = False
          else:
            LOG.warning('Unknown command: %s', line)
          continue

        rawdata, ip_from = fdin.recvfrom(1024)
        packet = wsjtx.ft8_decode(rawdata)
        if isinstance(packet, wsjtx.WSHeartbeat):
          pass
        elif isinstance(packet, wsjtx.WSLogged):
          self.current = None
          self.queue.put((DBCommand.STATUS, dict(call=packet.DXCall, status=2)))
          LOG.info("Logged call: %s, Grid: %s, Mode: %s",
                   packet.DXCall, packet.DXGrid, packet.Mode)
          ### Fix this
          log_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
          log_sock.sendto(packet.raw(), ('127.0.0.1', 2237))

        elif isinstance(packet, wsjtx.WSDecode):
          try:
            name, match = self.parser(packet.Message)
          except TypeError as err:
            LOG.error('Error: %s - Message: %s', err, packet.Message)
            continue

          if name is None:
            continue
          if name == 'REPLY' and match['call'] == self.current and match['to'] != self.mycall:
            LOG.info("Stop Transmit: %s Replying to %s ", match['call'], match['to'])
            self.stop_transmit(ip_from)
            self.queue.put((DBCommand.DELETE, match))
          elif name == 'CQ':
            match['frequency'] = frequency
            match['packet'] = packet.as_dict()
            self.queue.put((DBCommand.INSERT, match))

        elif isinstance(packet, wsjtx.WSStatus):
          frequency = packet.Frequency
          tx_status = any([packet.Transmitting, packet.TXEnabled])

          if (packet.Transmitting and packet.DXCall):
            self.queue.put((DBCommand.STATUS, dict(call=packet.DXCall, status=1)))

          if not packet.TXWatchdog and tx_status:
            continue
          LOG.debug("%s => TX: %s, TXEnabled: %s - TXWatchdog: %s", packet.DXCall,
                   packet.Transmitting, packet.TXEnabled, packet.TXWatchdog)

      ## Outside the for loop ##
      if not tx_status and sequence == 14:
        data = self.selector()
        if pause == True:
          continue

        if data:
          self.call_station(ip_from, data)
          time.sleep(1)
          self.current = data['call']
        else:
          self.current = None


class Plugins:

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

  def __call__(self):
    for selector in self.call_select:
      data = selector.get()
      if not data:
        continue
      name = selector.__class__.__name__
      LOG.info(('Calling: %s, From: %s, SNR: %d, Distance: %d, Frequency: %d MHz '
                'Selector: %s - https://www.qrz.com/db/%s'),
               data['call'], data['country'], data['snr'], data['distance'],
               data['frequency'] / 10**6, name, data['call'])
      return data
    return None


def main():
  global LOG
  logging.basicConfig(
    format='%(asctime)s - %(levelname)s[%(lineno)d] - %(message)s',
    datefmt='%H:%M:%S', level=logging.INFO
  )
  loglevel = os.getenv('LOGLEVEL', 'INFO')
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

  LOG.info('Call selector: %s', config.call_selector)
  call_select = Plugins(config.call_selector)
  main_loop = Sequencer(config, queue, call_select)
  try:
    main_loop.run()
  except KeyboardInterrupt:
    LOG.info('^C pressed exiting')

if __name__ == '__main__':
  main()
