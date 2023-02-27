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
from dbutils import DBCommand

from config import Config

RE_CQ = re.compile(r'^CQ ((?P<extra>.*) |)(?P<call>\w+)(|/\w+) (?P<grid>[A-Z]{2}[0-9]{2})')
RE_REPLY = re.compile(r'^((?!CQ)(?P<to>\w+)(|/\w+)) (?P<call>\w+)(|/\w+) (?P<grid>[A-Z]{2}[0-9]{2})')

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


  def check_reply(self, msg, packet):
    if msg['call'] == self.current and msg['to'] != 'W6BSD':
      print('*'* 50, foo['to'], foo['call'])

  def run(self):
    ip_from = None
    tx_status = False
    frequency = 0
    self.current = None
    while True:
      fds, _, _ = select.select([self.sock], [], [], .5)
      sequence = int(time.time()) % 15
      for fdin in fds:
        rawdata, ip_from = fdin.recvfrom(1024)
        packet = wsjtx.ft8_decode(rawdata)
        if isinstance(packet, wsjtx.WSHeartbeat):
          pass
        elif isinstance(packet, wsjtx.WSLogged):
          self.current = None
          self.queue.put((DBCommand.STATUS, dict(call=packet.DXCall, status=2)))
          LOG.info(str(packet))
        elif isinstance(packet, wsjtx.WSDecode):
          match = RE_REPLY.match(packet.Message)
          if match:
            self.check_reply(match.groupdict(), packet)

          # Handling CQ
          match = RE_CQ.match(packet.Message)
          if match:
            caller = match.groupdict()
            caller['frequency'] = frequency
            caller['packet'] = packet.as_dict()
            self.queue.put((DBCommand.INSERT, caller))

        elif isinstance(packet, wsjtx.WSStatus):
          frequency = packet.Frequency
          tx_status = any([packet.Transmitting, packet.TXEnabled])

          if (packet.Transmitting and packet.DXCall):
            self.queue.put((DBCommand.STATUS, dict(call=packet.DXCall, status=1)))

          if not packet.TXWatchdog and tx_status:
            continue
          LOG.warning("%s => TX: %s, TXEnabled: %s - TXWatchdog: %s", packet.DXCall,
                      packet.Transmitting, packet.TXEnabled, packet.TXWatchdog)

      ## Outside the for loop ##
      if not tx_status and sequence == 1:
        data = self.selector()
        if data:
          LOG.info('Calling: http://www.qrz.com/db/%s SNR: %d Distance: %d',
                   data['call'], data['snr'], data['distance'])
          self.call_station(ip_from, data['call'])
          time.sleep(1)
          self.current = data['call']
        else:
          self.current = None
          LOG.info('No call selected')


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
  loglevel = os.getenv('LOGLEVEL', 'INFO')
  if loglevel not in logging._nameToLevel: # pylint: disable=protected-access
    logging.error('Log level "%s" does not exist, defaulting to INFO', loglevel)
    loglevel = logging.INFO
  logging.root.setLevel(loglevel)
  LOG = logging.getLogger('Auto_FT8')

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
  main_loop = Sequencer(config, queue, call_select)
  main_loop.run()

if __name__ == '__main__':
  main()
