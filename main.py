"""The main module for the APK Crawler application."""

import sys
import subprocess
import os
import crawlui

# os.environ['ANDROID_ADB_SERVER_PORT'] = '5554'
_APK_DIR = os.path.dirname(os.path.abspath(__file__)) + '/apks/'


# PyDev sets PYTHONPATH, use it
try:
  for p in os.environ['PYTHONPATH'].split(':'):
    if not p in sys.path:
      sys.path.append(p)
except:
  pass

try:
  sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except:
  pass

from com.dtmilano.android.viewclient import ViewClient


if __name__ == '__main__':

  kwargs1 = {'verbose': True, 'ignoresecuredevice': True}
  kwargs2 = {'startviewserver': True, 'forceviewserveruse': False,
             'autodump': False, 'ignoreuiautomatorkilled': True}
  device, serialno = ViewClient.connectToDeviceOrExit(**kwargs1)
  vc = ViewClient(device, serialno, **kwargs2)

  # Simple setup
  # device, serialno = ViewClient.connectToDeviceOrExit()
  # vc = ViewClient(device, serialno)
  # vc = ViewClient(*ViewClient.connectToDeviceOrExit())

  # TODO (afergan): In the future we will go through all apps, but for
  # development, we can just specify 1 app.
  # package_list = os.listdir(_APK_DIR)
  # for package in package_list:

  # For now, just use one application.
  package = 'com.google.zagat.apk'
  app_name = package.split('.apk')[0]
  print app_name
  crawlui.crawl_package(_APK_DIR, app_name, vc, device)