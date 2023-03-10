#
# BSD 3-Clause License
#
# Copyright (c) 2023 Fred W6BSD
# All rights reserved.
#
#

import os
import logging
import sys

import yaml

CONFIG_FILENAME = "ft8ctrl.yaml"
CONFIG_LOCATIONS = ['/etc', '~/.local', '.']

class Config:
  _instance = None
  config_data = None
  def __new__(cls, *args, **kwargs):
    # pylint: disable=unused-argument
    if cls._instance is None:
      cls._instance = super(Config, cls).__new__(cls)
      cls._instance.config_data = {}
    return cls._instance

  def __init__(self, config_filename=None):
    self.log = logging.getLogger('Config')
    if self.config_data:
      return

    if config_filename:
      filename = config_filename
      if os.path.exists(filename):
        self.log.debug('Reading config file: %s', filename)
        self._readconfig(filename)
        return
      self.log.error('User configuration file "%s" not found. '
                     'Opening the default confuration file.', filename)

    config_filename = CONFIG_FILENAME
    for path in CONFIG_LOCATIONS:
      filename = os.path.expanduser(os.path.join(path, config_filename))
      if os.path.exists(filename):
        self.log.debug('Reading config file: %s', filename)
        self._readconfig(filename)
        return

    self.log.error('Configuration file "%s" not found', config_filename)
    sys.exit(os.EX_CONFIG)

  def _readconfig(self, filename):
      try:
        self.config_filename = filename
        self.config_data = self._read_config(filename)
      except ValueError as err:
        self.log.error('Configuration error "%s"', err)
        sys.exit(os.EX_CONFIG)
      except yaml.scanner.ScannerError as err:
        self.log.error('Configuration file syntax error: %s', err)
        sys.exit(os.EX_CONFIG)


  def __repr__(self):
    myself = super().__repr__()
    return f"{myself} file: {self.config_filename}"

  def to_yaml(self):
    return yaml.dump(self.config_data)

  def get(self, key, default=None):
    try:
      return self[key]
    except KeyError:
      return default

  def __getitem__(self, attr):
    if '.' in attr:
      section, attribute = attr.split('.')
    else:
      section = attr
      attribute = None
    if section not in self.config_data:
      raise KeyError(f'"Config" object has no section "{section}"')
    if not attribute:
      if not self.config_data[section]:
        return None
      config = type(section, (object, ), self.config_data[section])
      return config
    config = self.config_data[section]
    if attribute not in config:
      raise KeyError(f'"Config" object has no attribute "{attr}"')
    return config[attribute]

  @staticmethod
  def _read_config(filename):
    with open(filename, 'r', encoding='utf-8') as confd:
      configuration = yaml.safe_load(confd)
    return configuration
