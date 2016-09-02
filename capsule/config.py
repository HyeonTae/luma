# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""Config class definition."""

from ConfigParser import SafeConfigParser

CONFIG_FILE = 'config.ini'


class Config(object):
  """Class that contains all config info for the crawler.

  Includes information for text fields that should be populated.
  """

  def __init__(self):
    """Constructor for Config class."""

    # Loads info from CONFIG_FILE into self.data
    self.data = {}
    parser = SafeConfigParser()
    parser.read(CONFIG_FILE)
    for section_name in parser.sections():
      for name, value in parser.items(section_name):
        self.data[name] = value
