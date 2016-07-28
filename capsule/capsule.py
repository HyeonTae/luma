# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""The main module for the APK Crawler application."""

import os
import subprocess
import sys

from com.dtmilano.android.common import obtainAdbPath
from com.dtmilano.android.viewclient import ViewClient
import crawlpkg

ADB_PATH = obtainAdbPath()
# os.environ['ANDROID_ADB_SERVER_PORT'] = '5554'
APK_DIR = os.path.dirname(os.path.abspath(__file__)) + '/apks/'
# Whether we should skip the install & load process and just run the program
# on the currently loaded app.
DEBUG = True

# PyDev sets PYTHONPATH, use it
try:
  for p in os.environ['PYTHONPATH'].split(':'):
    if p not in sys.path:
      sys.path.append(p)
except KeyError:
  print 'Please set the environment variable PYTHONPATH'

try:
  sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except KeyError:
  print 'Please set the environment variable ANDROID_VIEW_CLIENT_HOME'


if __name__ == '__main__':
  kwargs1 = {'verbose': True, 'ignoresecuredevice': True}
  kwargs2 = {'startviewserver': True, 'forceviewserveruse': True,
             'autodump': False, 'ignoreuiautomatorkilled': True}
  device, serialno = ViewClient.connectToDeviceOrExit(**kwargs1)
  vc = ViewClient(device, serialno, **kwargs2)

  if DEBUG:
    crawlpkg.crawl_package(vc, device)
  else:
    package_list = sorted(os.listdir(APK_DIR))
    for package in package_list:
      # Install and crawl the app. device.shell() does not support the install
      # or launch.
      # Install the app.
      subprocess.call([ADB_PATH, 'install', '-r',
                       APK_DIR + package])
      if '.apk' in package:
        package_name = os.path.splitext(package)[0]
      else:
        # If the apk is saved without the extension.
        package_name = package

      print 'Crawling ' + package_name
      # Launch the app.
      subprocess.call([ADB_PATH, 'shell', 'monkey', '-p', package_name, '-c',
                       'android.intent.category.LAUNCHER', '1'])

      crawlpkg.crawl_package(vc, device, package_name)
      subprocess.call([ADB_PATH, 'uninstall', package_name])
