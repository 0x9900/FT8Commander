#
# BSD 3-Clause License
#
# Copyright (c) 2023 Fred W6BSD
# All rights reserved.
#
#

import logging
from pathlib import Path

import yaml

CONFIG_FILENAME = "ft8ctrl.yaml"
CONFIG_LOCATIONS = ['/etc', '~/.local/etc', '.']


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
    self.log = logging.getLogger('ft8ctrl.config')
    if self.config_data:
      return

    if config_filename:
      filename = Path(config_filename).expanduser()
      if filename.exists():
        self.log.debug('Reading config file: %s', filename)
        self.config_data = self._readconfig(filename)
        self.config_filename = filename
        return
      self.log.error('User configuration file "%s" not found.', filename)
      raise SystemExit('Configuration file error')

    config_filename = CONFIG_FILENAME
    for path in CONFIG_LOCATIONS:
      filename = Path(path).joinpath(config_filename).expanduser()
      if filename.exists():
        self.log.debug('Reading config file: %s', filename)
        self.config_data = self._readconfig(filename)
        self.config_filename = filename
        return

    self.log.error('Configuration file found')
    raise SystemExit('Config error')

  def _readconfig(self, filename):
    try:
      with open(filename, 'r', encoding='utf-8') as confd:
        config_data = yaml.safe_load(confd)
    except ValueError as err:
      self.log.error('Configuration error "%s"', err)
      raise SystemExit('Config error') from None
    except (yaml.parser.ParserError, yaml.scanner.ScannerError) as err:
      self.log.error('Configuration file syntax error: %s', err)
      raise SystemExit('Config file error') from None
    return config_data

  def __repr__(self):
    myself = super().__repr__()
    return f"{myself} file: {self.config_filename}"

  def to_yaml(self):
    return yaml.dump(self.config_data, explicit_start=True)

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
      if not isinstance(self.config_data[section], dict):
        return self.config_data[section]

      config = type(section, (object, ), self.config_data[section])
      return config

    config = self.config_data[section]
    if attribute not in config:
      raise KeyError(f'"Config" object has no attribute "{attr}"')
    return config[attribute]
