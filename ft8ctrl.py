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

from importlib import import_module
from queue import Queue

import wsjtx

from dbutils import create_db, get_call, DBInsert, Purge
from dbutils import INSERT, STATUS

from config import Config

RE_CQ = re.compile(r'^CQ ((?P<extra>.*) |)(?P<call>\w+)(|/\w+) (?P<grid>[A-Z]{2}[0-9]{2})')

LOG = logging.root

class Sequencer:
  def __init__(self, config, queue, call_select):
    self.db_name = config.db_name
    self.queue = queue
    self.selector = call_select
    self.follow_frequency = config.follow_frequency

    bind_addr = socket.gethostbyname(config.wsjt_ip)
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.sock.setblocking(False) # Set socket to non-blocking mode
    self.sock.bind((bind_addr, config.wsjt_port))

  def call_station(self, ip_from, call):
    data = get_call(self.db_name, call)
    if not data:
      return
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

  def run(self):
    frequency = 0
    ip_from = None
    tx_status = False
    while True:
      fds, _, _ = select.select([self.sock], [], [], .5)
      sequence = int(time.time()) % 15
      for fdin in fds:
        rawdata, ip_from = fdin.recvfrom(1024)
        packet = wsjtx.ft8_decode(rawdata)
        if isinstance(packet, wsjtx.WSHeartbeat):
          pass
        elif isinstance(packet, wsjtx.WSDecode):
          match = RE_CQ.match(packet.Message)
          if not match:
            continue
          caller = match.groupdict()
          caller['frequency'] = frequency
          caller['packet'] = packet.as_dict()
          self.queue.put((INSERT, caller))
        elif isinstance(packet, wsjtx.WSStatus):
          frequency = packet.Frequency
          tx_status = any([packet.Transmitting, packet.TXEnabled])

          if (packet.Transmitting and packet.DXCall):
            self.queue.put((STATUS, dict(call=packet.DXCall, status=1)))

          if not packet.TXWatchdog and tx_status:
            continue
          LOG.warning("%s => TX: %s, TXEnabled: %s - TXWatchdog: %s", packet.DXCall,
                      packet.Transmitting, packet.TXEnabled, packet.TXWatchdog)

        elif isinstance(packet, wsjtx.WSLogged):
          self.queue.put((STATUS, dict(call=packet.DXCall, status=2)))
          LOG.info(str(packet))

      if not tx_status and sequence == 1:
        data = self.selector()
        if data:
          LOG.info('Calling: %s SNR: %d Distance: %f', data['call'], data['snr'], data['distance'])
          self.call_station(ip_from, data['call'])
        else:
          LOG.info('No call selected')
        time.sleep(1)

class Plugins:

  def __init__(self, plugins):
    # Download plugins
    self.call_select = []
    if isinstance(plugins, str):
      plugins = [plugins]

    for plugin in plugins:
      *module_name, class_name = plugin.split('.')
      module_name = '.'.join(['plugins'] + module_name)
      module = import_module(module_name)
      klass = getattr(module, class_name)
      self.call_select.append(klass())

  def next(self):
    call = None
    for selector in self.call_select:
      call = selector.get()
      if call:
        LOG.debug('Selector: %s (%s)', selector.__class__.__name__, call['call'])
        break
    return call


def main():
  global LOG
  config = Config()['ft8ctrl']

  logging.basicConfig(
    format='%(asctime)s - %(levelname)s[%(lineno)d] - %(message)s',
    datefmt='%H:%M:%S', level=logging.INFO
  )
  LOG = logging.getLogger('Auto_FT8')
  loglevel = os.getenv('LOGLEVEL', 'INFO')
  if loglevel not in logging._nameToLevel: # pylint: disable=protected-access
    LOG.error('Log level "%s" does not exist, defaulting to INFO', loglevel)
    loglevel = logging.INFO
  LOG.setLevel(loglevel)

  create_db(config.db_name)

  queue = Queue()
  db_thread = DBInsert(config.db_name, queue)
  db_thread.daemon = True
  db_thread.start()

  db_purge = Purge(config.db_name, config.purge_time)
  db_purge.daemon = True
  db_purge.start()

  LOG.info('Call selector: %s', config.call_selector)
  call_select = Plugins(config.call_selector)
  main_loop = Sequencer(config, queue, call_select.next)
  main_loop.run()

if __name__ == '__main__':
  main()
