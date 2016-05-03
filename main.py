"""The main module for the APK Crawler application."""

import sys
import subprocess
import os
import crawlui

_ADB_PATH = os.path.expanduser('~') + "/Android/Sdk/platform-tools/adb"
_APK_DIR = os.path.dirname(os.path.abspath(__file__)) + "/apks/"

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
  kwargs2 = {'startviewserver': True, 'forceviewserveruse': True,
             'autodump': False, 'ignoreuiautomatorkilled': True}
  device, serialno = ViewClient.connectToDeviceOrExit(**kwargs1)
  vc = ViewClient(device, serialno, **kwargs2)

  # Simple setup
  #device, serialno = ViewClient.connectToDeviceOrExit()
  #vc = ViewClient(device, serialno)

  package_list = os.listdir(_APK_DIR)
  for package in package_list:
    app_name = package.split(".apk")[0]
    print app_name
    crawlui.crawl_package(_APK_DIR, app_name, vc, device)
