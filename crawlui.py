"""A module for installing and crawling the UI of Android application."""

import subprocess
import sys
import os
import time

# Linux ADB path
ADB_PATH = os.path.expanduser('~') + '/Android/Sdk/platform-tools/adb'
# OS X ADB path
#ADB_PATH = '/usr/local/bin/adb'

from com.dtmilano.android.viewclient import ViewClient, ViewClient
from subprocess import check_output


def get_activity_name(package_name, vc):
  """Gets the current running activity of the package."""
  proc = subprocess.Popen([ADB_PATH, 'shell', 'dumpsys window windows '
                          '| grep -E \'mCurrentFocus\''],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  activity_str, err = proc.communicate()
  # The current focus returns a string in the format
  # mCurrentFocus=Window{35f66c3 u0 com.google.zagat/com.google.android.apps.
  # zagat.activities.BrowseListsActivity}
  # We only want the text between the final period and the closing bracket.
  return activity_str.split('.')[-1].split('}')[0]

def save_screenshot(directory, activity):
  screenshot_num = 0
  while os.path.exists(
        directory + '/' + activity + str(screenshot_num) + '.png'):
    screenshot_num += 1
  screenname = activity + str(screenshot_num) + '.png'
  subprocess.call([ADB_PATH, 'shell', 'screencap', '/sdcard/' + screenname])
  subprocess.call([ADB_PATH, 'pull', '/sdcard/' + screenname,
                  directory + '/' + screenname])

def crawl_activity(package_name, vc, device):
  directory = (os.path.dirname(os.path.abspath(__file__)) + '/data/'
               + package_name)
  if not os.path.exists(directory):
    os.makedirs(directory)
  view = vc.dump(window='-1')
  activity = get_activity_name(package_name, vc)
  save_screenshot(directory, activity)
  clickable_components = []

  # Print the details of every component in the view.
  for component in view:
    if (component.isClickable()):
      clickable_components.append(component)

  for c in clickable_components:
    print 'Clickable:' + c['uniqueId'] + ' ' + c['class']
    subprocess.call([ADB_PATH, 'shell', 'input', 'tap', str(c.getXY()[0]),
                    str(c.getXY()[1])])
    time.sleep(1)
    crawl_activity(package_name, vc, device)

def crawl_package(apk_dir, package_name, vc, device, debug):

  if (not(debug)):
    # Install the app.
    subprocess.call([ADB_PATH, 'install', '-r', apk_dir + package_name
      + '.apk'])

    #Launch the app.
    subprocess.call([ADB_PATH, 'shell', 'monkey', '-p', package_name, '-c',
                    'android.intent.category.LAUNCHER', '1'])

  crawl_activity(package_name, vc, device)