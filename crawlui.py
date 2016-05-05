"""A module for installing and crawling the UI of Android application."""

import subprocess
import sys
import os

# Linux ADB path
_ADB_PATH = os.path.expanduser('~') + "/Android/Sdk/platform-tools/adb"
# OS X ADB path
#_ADB_PATH = "/usr/local/bin/adb"

from com.dtmilano.android.viewclient import ViewClient, ViewClient


def get_activity_name(package_name, vc):
  """Gets the current running activity of the package."""
  # TODO(afergan): If there are multiple windows of the application open, make
  # sure we are getting the top window.
  windows = vc.list()
  for wId in windows.keys():
    if package_name in windows[wId]:
      return windows[wId].split(".")[-1]

def crawl_activity(package_name, vc, device):

  screenshot_num = 0
  directory = (os.path.dirname(os.path.abspath(__file__)) + "/data/"
               + package_name)
  if not os.path.exists(directory):
    os.makedirs(directory)
  view = vc.dump(window='-1')
  activity = get_activity_name(package_name, vc)
  filename = directory + "/" + activity + str(screenshot_num) + ".png"
  # If the screenshot already exists, increment the filename.
  while os.path.exists(filename):
    screenshot_num += 1
    filename = directory + "/" + activity + str(screenshot_num) + ".png"

  device.takeSnapshot().save(filename, 'PNG')
  screenshot_num += 1

  clickable_components = []

  # Print the details of every component in the view.
  for component in view:
    # print ">>Component: ", component
    if (component.isClickable()):
      clickable_components.append(component)

  # Print only the names of clickable components.
  for c in clickable_components:
    print "Clickable: " + c['uniqueId'] + " " + c['class']

def crawl_package(apk_dir, package_name, vc, device):

  # Install the app.
  # subprocess.call([_ADB_PATH, 'install', '-r', apk_dir + package_name + ".apk"])

  # Launch the app.
  # subprocess.call([_ADB_PATH, 'shell', 'monkey', '-p', package_name, '-c',
                #    'android.intent.category.LAUNCHER', '1'])

  crawl_activity(package_name, vc, device)

