"""A module for installing and crawling the UI of Android application."""

import re
import subprocess
import sys
import os
import time

# Linux ADB path
#ADB_PATH = os.path.expanduser('~') + '/Android/Sdk/platform-tools/adb'
# OS X ADB path
ADB_PATH = '/usr/local/bin/adb'

from com.dtmilano.android.viewclient import ViewClient, ViewClient
from subprocess import check_output
from view import View


def get_activity_name():
  """Gets the current running activity of the package."""
  proc = subprocess.Popen([ADB_PATH, 'shell', 'dumpsys window windows '
                          '| grep -E \'mCurrentFocus\''],
                          stdout = subprocess.PIPE, stderr = subprocess.PIPE)
  activity_str, err = proc.communicate()
  # The current focus returns a string in the format
  # mCurrentFocus=Window{35f66c3 u0 com.google.zagat/com.google.android.apps.
  # zagat.activities.BrowseListsActivity}
  # We only want the text between the final period and the closing bracket.
  return activity_str.split('.')[-1].split('}')[0]

def get_fragment_name(package_name):
  """Gets the current top fragment of the package."""
  proc = subprocess.Popen([ADB_PATH, 'shell', 'dumpsys activity ',
                          package_name, ' | grep -E '
                          '\'Local FragmentActivity\''], stdout =
                          subprocess.PIPE, stderr = subprocess.PIPE)
  fragment_str, err = proc.communicate()
  return re.search("Local FragmentActivity (.*?) State:",fragment_str).group(1)

def save_screenshot(package_name):
  directory = (os.path.dirname(os.path.abspath(__file__)) + '/data/'
               + package_name)
  if not os.path.exists(directory):
    os.makedirs(directory)
  screenshot_num = 0
  activity = get_activity_name()
  fragment = get_fragment_name(package_name)
  while os.path.exists(directory + '/' + activity + '-' + fragment + '-' + str(
                       screenshot_num) + '.png'):
    screenshot_num += 1
  screen_name = activity + '-' + fragment + '-' + str(screenshot_num) + '.png'
  print screen_name
  screen_path = directory + '/' + screen_name
  print screen_path
  subprocess.call([ADB_PATH, 'shell', 'screencap', '/sdcard/' + screen_name])
  subprocess.call([ADB_PATH, 'pull', '/sdcard/' + screen_name, screen_path])

  # Return the filename & num so that the screenshot can be accessed
  # programatically.
  return [screen_path, screenshot_num]

def crawl_activity(package_name, vc, device):
  curr_view = vc.dump(window='-1')
  clickable_components = []

  for component in curr_view:
    print component
    if component.isClickable():
      clickable_components.append(component)

  for c in clickable_components:
    print 'Clickable:' + c['uniqueId'] + ' ' + c['class'] + str(c.getXY())
    subprocess.call([ADB_PATH, 'shell', 'input', 'tap', str(c.getXY()[0]),
                    str(c.getXY()[1])])
    time.sleep(1)

    # TODO (afergan): check for duplicates
    v = View(get_activity_name(), get_fragment_name(package_name))
    v.hierarchy = curr_view
    screenshot_info = save_screenshot(package_name)
    v.screenshot = screenshot_info[0]
    v.num = screenshot_info[1]
    v.print_info()

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