"""A module for installing and crawling the UI of Android application."""

import re
import subprocess
import sys
import os
import time

# Linux ADB path
ADB_PATH = os.path.expanduser('~') + '/Android/Sdk/platform-tools/adb'
# OS X ADB path
#ADB_PATH = '/usr/local/bin/adb'

MAX_WIDTH = 1080
# TODO(afergan): For layouts longer than the width of the screen, scroll down
# and click on them. For now, we ignore them.
MAX_HEIGHT = 1920
NAVBAR_HEIGHT = 63

# Visibility
VISIBLE = 0x0
INVISIBLE = 0x4
GONE = 0x8

from com.dtmilano.android.viewclient import ViewClient
from subprocess import check_output
from view import View

view_root = []
view_array = []

def perform_press_back():
  subprocess.call([ADB_PATH, 'shell', 'input', 'keyevent', '4'])

def get_activity_name():
  """Gets the current running activity of the package."""
  # TODO(afergan): Make sure we are still running the correct package and have
  # not exited or redirected to a different app.

  proc = subprocess.Popen([ADB_PATH, 'shell', 'dumpsys window windows '
                          '| grep -E \'mCurrentFocus\''],
                          stdout = subprocess.PIPE, stderr = subprocess.PIPE)
  activity_str, err = proc.communicate()

  # If a popup menu has captured the focus, the focus will be in the format
  # mCurrentFocus=Window{8f1328e u0 PopupWindow:53a5957}
  if 'PopupWindow' in activity_str:
    popup_str = activity_str[activity_str.find('PopupWindow'):].split('}')[0]
    return popup_str.replace(':','')

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

  fragment_name = re.search('Local FragmentActivity (.*?) State:',fragment_str)
  if fragment_name is None:
    return 'NoFrag'
  return re.search('Local FragmentActivity (.*?) State:',fragment_str).group(1)

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
  subprocess.call([ADB_PATH, 'shell', 'screencap', '/sdcard/' + screen_name])
  subprocess.call([ADB_PATH, 'pull', '/sdcard/' + screen_name, screen_path])

  # Return the filename & num so that the screenshot can be accessed
  # programatically.
  return [screen_path, screenshot_num]

def find_view_idx(package_name, vc_dump):
  for i in range(len(view_array)):
    if view_array[i].is_duplicate(get_activity_name(),
                                  get_fragment_name(package_name), vc_dump):
      return i
  return -1

def create_view(package_name, vc_dump):
  v = View(get_activity_name(), get_fragment_name(package_name))
  v.hierarchy = vc_dump

  for component in v.hierarchy:
    # TODO(afergan): For now, only click on certain components, and allow custom
    # components. Evaluate later if this is worth it or if we should just click
    # on everything attributed as clickable.

    # TODO(afergan): Should we include clickable ImageViews? Seems like a lot of
    # false clicks for this so far...
    if (component.isClickable() and component.getVisibility() == VISIBLE and
        component.getX() >= 2 and component.getY() <= MAX_WIDTH and
        component['layout:layout_width'] > 0 and
        component.getY() >= (NAVBAR_HEIGHT + 2) and
        component.getY() <= MAX_HEIGHT and
        component['layout:layout_height'] > 0 and
        ('Button' in component['class'] or
        (component ['class'] ==
        'com.android.settings.dashboard.DashboardTileView')  or
        component['class'] == 'android.widget.ImageView' or
        'ActionMenuItemView' in component['class'] or
        'TextView' in component['class'] or
        'android' not in component['class'] or
        'Spinner' in component['class'] or
        component.parent == 'android.widget.ListView')):
          print component['class'] + '-- will be clicked'
          v.clickable.append(component)

  screenshot_info = save_screenshot(package_name)
  v.screenshot = screenshot_info[0]
  v.num = screenshot_info[1]

  return v

def crawl_activity(package_name, vc, device):
  vc_dump = vc.dump(window='-1')

  # Returning to a view that has already been seen.
  view_idx = find_view_idx(package_name, vc_dump)
  if view_idx >= 0:
    print('**FOUND DUPLICATE')
    curr_view = view_array[view_idx]
  else:
    print('**NEW VIEW')
    curr_view = create_view(package_name, vc_dump)
    view_array.append(curr_view)

  print 'Num clickable: ' + str(len(curr_view.clickable))

  if len(curr_view.clickable) > 0:
    c = curr_view.clickable[0]
    print c
    print ('Clickable: ' + c['uniqueId'] + ' ' + c['class'] + ' ' +
      str(c.getX()) + ' ' + str(c.getY()))
    subprocess.call([ADB_PATH, 'shell', 'input', 'tap', str(c.getX()),
                   str(c.getY())])
    print str(len(curr_view.clickable)) + ' elements left to click'
    del curr_view.clickable[0]

  else:
    print '!!! Clicking back button'
    if curr_view == view_root:
      return
    perform_press_back()

  crawl_activity(package_name, vc, device)

def crawl_package(apk_dir, package_name, vc, device, debug):
  if (not(debug)):
    # Install the app.
    subprocess.call([ADB_PATH, 'install', '-r', apk_dir + package_name
                    + '.apk'])
    #Launch the app.
    subprocess.call([ADB_PATH, 'shell', 'monkey', '-p', package_name, '-c',
                    'android.intent.category.LAUNCHER', '1'])

  #Store the root View
  print 'Storing root'
  vc_dump = vc.dump(window='-1')
  view_root = create_view(package_name, vc_dump)
  view_array.append(view_root)

  crawl_activity(package_name, vc, device)