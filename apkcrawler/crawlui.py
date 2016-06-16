# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""A module for installing and crawling the UI of Android application."""

import copy
import json
import os
import re
import subprocess

from view import View


ADB_PATH = None

# Nexus 6 dimensions.
MAX_WIDTH = 1440
# TODO(afergan): For layouts longer than the width of the screen, scroll down
# and click on them. For now, we ignore them.
MAX_HEIGHT = 2560
NAVBAR_HEIGHT = 84

# Visibility
VISIBLE = 0x0
INVISIBLE = 0x4
GONE = 0x8

# Return a unique string if the package is not the focused window. Since
# activities cannot have spaces, we ensure that no activity will be named this.
EXITED_APP = 'exited app'


def set_adb_path():
  """Define the ADB path based on operating system."""
  try:
    global ADB_PATH
    # For machines with multiple installations of adb, use the last listed
    # version of adb. If this doesn't work for your setup, modify to taste.
    ADB_PATH = subprocess.check_output(['which -a adb'], shell=True).split(
        '\n')[-2]
  except subprocess.CalledProcessError:
    print 'Could not find adb. Please check your PATH.'


def perform_press_back():
  subprocess.call([ADB_PATH, 'shell', 'input', 'keyevent', '4'])


def get_activity_name(package_name):
  """Gets the current running activity of the package."""
  # TODO(afergan): See if we can consolidate this with get_fragment_list, but
  # still make sure that the current app has focus.
  # TODO(afergan): Check for Windows compatibility.
  proc = subprocess.Popen([ADB_PATH, 'shell', 'dumpsys window windows '
                                              '| grep -E \'mCurrentFocus\''],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  activity_str, _ = proc.communicate()

  # If a popup menu has captured the focus, the focus will be in the format
  # mCurrentFocus=Window{8f1328e u0 PopupWindow:53a5957}
  if 'PopupWindow' in activity_str:
    popup_str = activity_str[activity_str.find('PopupWindow'):].split('}')[0]
    return popup_str.replace(':', '')

  # We are no longer in the app.
  if package_name not in activity_str:
    print 'Exited app'
    # If app opened a different app, try to get back to it.
    perform_press_back()
    if package_name not in activity_str:
      return EXITED_APP

  # The current focus returns a string in the format
  # mCurrentFocus=Window{35f66c3 u0 com.google.zagat/com.google.android.apps.
  # zagat.activities.BrowseListsActivity}
  # We only want the text between the final period and the closing bracket.
  return activity_str.split('.')[-1].split('}')[0]


def get_frag_list(package_name):
  """Gets the list of fragments in the current view."""
  proc = subprocess.Popen([ADB_PATH, 'shell', 'dumpsys activity', package_name],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  adb_dump, _ = proc.communicate()
  frag_dump = re.findall('Added Fragments:(.*?)FragmentManager', adb_dump,
                         re.DOTALL)
  if not frag_dump:
    return 'NoFrag'
  frag_list = re.findall(': (.*?){', frag_dump[0], re.DOTALL)
  print frag_list
  return frag_list


def get_package_name():
  """Get the package name of the current focused window."""
  proc = subprocess.Popen([ADB_PATH, 'shell', 'dumpsys window windows '
                                              '| grep -E \'mCurrentFocus\''],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  activity_str, _ = proc.communicate()

  # The current focus returns a string in the format
  # mCurrentFocus=Window{35f66c3 u0 com.google.zagat/com.google.android.apps.
  # zagat.activities.BrowseListsActivity}
  # We want the text before the /
  pkg_name = activity_str.split('/')[0].split(' ')[-1]
  print 'Package name is ' + pkg_name
  return pkg_name


def save_view_data(package_name, activity, frag_list, vc_dump):
  """Store the screenshot with a unique filename."""
  directory = (os.path.dirname(os.path.abspath(__file__)) + '/data/'
               + package_name)
  if not os.path.exists(directory):
    os.makedirs(directory)
  file_num = 0
  dump_file = os.path.join(directory, activity + '-' + frag_list[0] + '-'
                           + str(file_num) + '.json')
  while os.path.exists(dump_file):
    file_num += 1
    dump_file = os.path.join(directory, activity + '-' + frag_list[0] + '-'
                             + str(file_num) + '.json')

  view_info = {}
  view_info['hierarchy'] = {}
  view_info['fragmentList'] = frag_list

  for component in vc_dump:
    # Because the children and parent are each instances, they are not JSON
    # serializable. We replace them with just the ids of the instances (and
    # discard the device info).
    dict_copy = copy.copy(component.__dict__)
    del dict_copy['device']
    if dict_copy['parent']:
      dict_copy['parent'] = dict_copy['parent']['uniqueId']
    dict_copy['children'] = []
    for child in component.__dict__['children']:
      dict_copy['children'].append(child['uniqueId'])
    view_info['hierarchy'][component['uniqueId']] = dict_copy

  with open(dump_file, 'w') as out_file:
    json.dump(view_info, out_file, indent=2)

  screen_name = (activity + '-' + frag_list[0] + '-' + str(file_num) + '.png')
  screen_path = os.path.join(directory, screen_name)
  subprocess.call([ADB_PATH, 'shell', 'screencap', '/sdcard/' + screen_name])
  subprocess.call([ADB_PATH, 'pull', '/sdcard/' + screen_name, screen_path])

  # Return the filename & num so that the screenshot can be accessed
  # programatically.
  return [screen_path, file_num]


def find_view_idx(vc_dump, activity, frag_list, view_array):
  """Find the index of the current View in the view array (-1 if new view)."""
  for i in range(len(view_array)):
    if view_array[i].is_duplicate(activity, frag_list, vc_dump):
      return i
  return -1


def create_view(package_name, vc_dump, activity, frag_list):
  """Store the current view in the View data structure."""
  screenshot_info = save_view_data(package_name, activity, frag_list, vc_dump)
  v = View(activity, frag_list, vc_dump, screenshot_info[0], screenshot_info[1])

  for component in v.hierarchy:
    # TODO(afergan): For now, only click on certain components, and allow custom
    # components. Evaluate later if this is worth it or if we should just click
    # on everything attributed as clickable.

    if (component.isClickable() and component.getVisibility() == VISIBLE and
        component.getX() >= 0 and component.getX() <= MAX_WIDTH and
        int(component['layout:getWidth()']) > 0 and
        component.getY() >= (NAVBAR_HEIGHT) and
        component.getY() <= MAX_HEIGHT and
        int(component['layout:getHeight()']) > 0):
      print component['class'] + '-- will be clicked'
      v.clickable.append(component)

  return v


def crawl_package(apk_dir, vc, device, debug, package_name=None):
  """Main crawler loop. Evaluate views, store new views, and click on items."""
  set_adb_path()
  view_root = []
  view_array = []

  if debug or not package_name:  # These should be equal
    package_name = get_package_name()
  else:
    # Install the app.
    subprocess.call([ADB_PATH, 'install', '-r', apk_dir + package_name
                     + '.apk'])
    # Launch the app.
    subprocess.call([ADB_PATH, 'shell', 'monkey', '-p', package_name, '-c',
                     'android.intent.category.LAUNCHER', '1'])

  # Store the root View
  print 'Storing root'
  vc_dump = vc.dump(window='-1')
  activity = get_activity_name(package_name)
  if activity == EXITED_APP:
    return
  frag_list = get_frag_list(package_name)
  view_root = create_view(package_name, vc_dump, activity, frag_list)
  view_array.append(view_root)
  curr_view = view_root

  while True:

    # If last click opened the keyboard, assume we're in the same view and just
    # click on the next element. Since opening the keyboard can leave traces of
    # additional components, don't check if view is duplicate.
    # TODO(afergan): Is this a safe assumption?
    if device.isKeyboardShown():
      perform_press_back()
    else:
      # Determine if this is a View that has already been seen.
      view_idx = find_view_idx(vc_dump, activity, frag_list, view_array)
      if view_idx >= 0:
        print '**FOUND DUPLICATE'
        curr_view = view_array[view_idx]
      else:
        print '**NEW VIEW'
        curr_view = create_view(package_name, vc_dump, activity, frag_list)
        view_array.append(curr_view)

    print 'Num clickable: ' + str(len(curr_view.clickable))

    if curr_view.clickable:
      c = curr_view.clickable[-1]
      print ('Clickable: {} {}, ({},{})'.format(c['uniqueId'], c['class'],
                                                c.getX(), c.getY()))
      subprocess.call([ADB_PATH, 'shell', 'input', 'tap', str(c.getX()),
                       str(c.getY())])
      print str(len(curr_view.clickable)) + ' elements left to click'
      del curr_view.clickable[-1]

    else:
      print '!!! Clicking back button'
      perform_press_back()
      if curr_view == view_root:
        return

    vc_dump = vc.dump(window='-1')
    activity = get_activity_name(package_name)
    if activity == EXITED_APP:
      return
    frag_list = get_frag_list(package_name)
