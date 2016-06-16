# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""The main module for the APK Crawler application."""

import os
import sys

from com.dtmilano.android.viewclient import ViewClient
import crawlui


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

  if not DEBUG:
    package_list = os.listdir(APK_DIR)
    for package in package_list:
      if '.apk' in package:
        package_name = os.path.splitext(package)[0]
        print package_name
        crawlui.crawl_package(APK_DIR, vc, device, DEBUG, package_name)
  else:
    crawlui.crawl_package(APK_DIR, vc, device, DEBUG)
