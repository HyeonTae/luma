"""A module for installing and crawling the UI of Android application."""

import subprocess
import sys
import os

_ADB_PATH = os.path.expanduser('~') + "/Android/Sdk/platform-tools/adb"

from com.dtmilano.android.viewclient import ViewClient, View

def crawl_package(apk_dir, package_name, vc, device):

  # Install the app.
  subprocess.call([_ADB_PATH, 'install', '-r', apk_dir + package_name + ".apk"])

  # Launch the app.
  subprocess.call([_ADB_PATH, 'shell', 'monkey', '-p', package_name, '-c',
                  'android.intent.category.LAUNCHER', '1'])

  view = vc.dump()

  # Print the details of every component in the view.
  for component in view:
      print ">>Component:", component

  # Print only the names of clickable components.
  for component in view:
    if (component.isClickable()):
      print ">>Clickable component:", component['uniqueId']
