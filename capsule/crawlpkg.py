# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.
"""A module for installing and crawling the UI of Android application."""

from collections import Counter
import copy
import json
import os
import re
import subprocess
import time

from com.dtmilano.android.common import obtainAdbPath

from config import Config
from layout import Layout

# https://material.google.com/layout/structure.html#structure-system-bars
NAVBAR_DP_HEIGHT = 48

MAX_X = 0
MAX_Y = 0
STATUS_BAR_HEIGHT = 0

# Visibility
VISIBLE = 0x0
INVISIBLE = 0x4
GONE = 0x8

ADB_PATH = obtainAdbPath()
SERIAL_NO = ''
BACK_BUTTON = 'back button'
# Return a unique string if the package is not the focused window. Since
# activities cannot have spaces, we ensure that no activity will be named this.
EXITED_APP = 'exited app'
FAILED_FINDING_NAME = 'failed finding name'
# How many times we should try pressing the back button to return to the app
# before giving up.
NUM_BACK_PRESSES = 3
# Number of dumps we'll try in a row before succumbing to socket timeouts and
# giving up.
MAX_DUMPS = 6
# To prevent getting stuck in apps with a large number of UIs or dynamic content
# that can change the view hierarchy each time it's loaded, we limit the number
# of crawls to perform and max number of layouts to store per app.
MAX_CRAWLS = 20
MAX_LAYOUTS = 40
# We use this to prevent loops that can occur when back button behavior creates
# a cycle.
MAX_CONSEC_BACK_PRESSES = 10
MAX_FB_AUTH_TAPS = 5
MAX_FB_BUG_RESETS = 5

NEGATIVE_WORDS = ['no', 'cancel', 'back', 'neg' 'deny', 'prev', 'exit',
                  'delete', 'end', 'remove', 'clear', 'reset', 'undo']


def extract_between(text, sub1, sub2, nth=1):
  """Extracts a substring from text between two given substrings."""
  # Credit to
  # https://www.daniweb.com/programming/software-development/code/446964/extract-a-string-between-2-substrings-python

  # Prevent sub2 from being ignored if it's not there.
  if sub2 not in text.split(sub1, nth)[-1]:
    return None
  return text.split(sub1, nth)[-1].split(sub2, nth)[0]


def set_device_dimens(vc, device):
  """Sets global variables to the dimensions of the device."""
  global MAX_X, MAX_Y, STATUS_BAR_HEIGHT

  try:
    # Returns a string similar to "Physical size: 1440x2560"
    size = device.shell('wm size')
    # Returns a string similar to "Physical density: 560"
    density = int(device.shell('wm density').split(' ')[-1])
    # We do not want the crawler to click on the navigation bar because it can
    # hit the back button or minimize the app.
    # From https://developer.android.com/guide/practices/screens_support.html
    # The conversion of dp units to screen pixels is simple:
    # px = dp * (dpi / 160)
    navbar_height = NAVBAR_DP_HEIGHT * density / 160
  except IOError:
    print '*** Socket timeout! Cannot get nav bar height.'
    navbar_height = 0

  MAX_X = int(extract_between(size, ': ', 'x'))
  MAX_Y = int(extract_between(size, 'x', '\r')) - navbar_height
  vc_dump = perform_vc_dump(vc)
  if vc_dump:
    STATUS_BAR_HEIGHT = (
        vc_dump[0].getY() - int(vc_dump[0]['layout:getLocationOnScreen_y()']))
  else:
    # Keep status at default 0 height.
    print 'Cannot get status bar height.'


def is_in_bounds(x, y):
  return x >= 0 and x <= MAX_X and y >= STATUS_BAR_HEIGHT and y <= MAX_Y


def perform_press_back(device):
  device.press('KEYCODE_BACK')


def perform_vc_dump(vc):
  try:
    return vc.dump(window='-1')
  except IOError:
    print '*** Socket timeout!'
    return None


def touch(device, view):
  """Touches the corner of a view."""

  # We don't use the AndroidViewClient view.touch() method because it touches
  # the center of the view, which may be offscreen (or push a button on the nav
  # bar).
  try:
    (x, y) = view.getXY()
    device.touch(x, y)
    print('Clicked  {} {}, ({},{})'.format(view.getUniqueId(),
                                           view.getClass(), view.getX(),
                                           view.getY()))
  except UnicodeEncodeError:
    print '***Unicode coordinates'
  except TypeError:
    print '***String coordinates'


def use_keyboard(prev_clicked, config_data, device, vc):
  """Type text when the keyboard is visible."""

  print 'Prev clicked: ' + prev_clicked
  view = vc.findViewById(prev_clicked)

  if not view:
    # Sometimes when we get to a new Layout, an EditText is already selected.
    # This means that prev_clicked will refer to a view from a previous Layout.
    # The currently selected view will be clicked again during our crawl, so do
    # not enter text now.

    # TODO(afergan): This is just to check which view is selected, but since the
    # dump takes time, remove this later.
    vc_dump = perform_vc_dump(vc)
    for v in vc_dump:
      if v.isFocused():
        print 'Focused: ' + v.getUniqueId()
        break

    perform_press_back(device)
    return

  # TODO(afergan): The dump does not include information about hints for the
  # TextView, which can be very useful in the absence of a descriptive view id.
  # See if there is a way to access this, or add this to our custom build of
  # AOSP.
  # https://developer.android.com/reference/android/widget/TextView.html#attr_android:hint)

  # If there is already text in the field, do not add additional text.
  if view and view.getText():
    print 'This text field is already populated.'
    perform_press_back(device)
    return

  # Check if the id contains any of the words in the [basic info] section of the
  # config. If any of these fields have been removed, do not type anything.
  if 'name' in prev_clicked:
    if any(x in prev_clicked for x in['last', 'sur']):
      print 'Typing last name ' + config_data.get('last_name', '')
      device.type(config_data.get('last_name', ''))
    else:
      print 'Typing first name ' + config_data.get('first_name', '')
      device.type(config_data.get('first_name', ''))
  elif any(x in prev_clicked for x in['email', 'mail', 'address']):
    print 'Typing email address ' + config_data.get('email', '')
    device.type(config_data.get('email', ''))
  elif any(x in prev_clicked for x in['password', 'pw']):
    print 'Typing password ' + config_data.get('password', '')
    device.type(config_data.get('password', ''))
  elif any(x in prev_clicked for x in['zip']):
    print 'Typing zip code ' + config_data.get('zipcode', '')
    device.type(config_data.get('zipcode', ''))
  elif any(x in prev_clicked for x in['phone']):
    print 'Typing phone number ' + config_data.get('phone_num', '')
    device.type(config_data.get('phone_num', ''))
  else:
    # If the user has added additional fields in the config, check for those.
    for c in config_data:
      if any(x in prev_clicked for x in c):
        device.type(config_data.get(c, ''))
        break
    else:
      print 'Typing default text ' + config_data.get('default', '')
      device.type(config_data.get('default', ''))

  # TODO(afergan): The enter key can sometimes advance us to the next field or
  # Layout, but we would have to track that here. For now, just minimize the
  # keyboard and let the crawler advance us.
  perform_press_back(device)
  return


def fb_login(package_name, device, curr_layout, click, vc):
  """Log into Facebook by automating the authentication flow."""

  # Get the full name of the current activity.
  focus_str = device.shell("dumpsys window windows | grep -E 'mCurrentFocus'")
  app_activity = extract_between(focus_str, ' ', '}', -1)
  print 'App activity: ' + app_activity
  print 'Trying to log into Facebook.'
  # Sometimes touch() doesn't work
  curr_layout.clickable.remove(click)
  device.shell('input tap ' + str(click.getX()) +
               ' ' + str(click.getY()))

  # Make sure the new screen is loaded by waiting for the dump.
  perform_vc_dump(vc)
  activity_str = obtain_focused_activity(device, vc)
  print activity_str

  # For a weird bug where the Facebook app sometimes repeatedly
  # flashes a splashscreen and does not advance to the login.
  f = 0
  while activity_str == 'com.facebook.katana.app.FacebookSplashScreenActivity':

    # We were not able to get past the bug.
    if f >= MAX_FB_BUG_RESETS:
      print 'Could not get past Facebook bug.'
      return False

    print 'Facebook bug! ' + str(f)
    # Clear, stop, and relaunch Facebook.
    device.shell('adb shell pm clear com.facebook.katana')
    device.shell('am force-stop com.facebook.katana')
    device.shell('monkey -p com.facebook.katana -c '
                 'android.intent.category.LAUNCHER 1')
    time.sleep(2)
    # Relaunch the app with the previous activity.
    out = device.shell('su 0 am start -n ' + app_activity)
    if any(x in out for x in['Error', 'Warning']):
      # TODO(afergan): Relaunch the app and follow the shortest path to here.
      return False

    time.sleep(5)
    device.shell('input tap ' + str(click.getX()) + ' ' + str(click.getY()))
    time.sleep(5)
    activity_str = obtain_focused_activity(device, vc)
    print activity_str
    f += 1

  activity_str = obtain_focused_activity(device, vc)

  if activity_str == 'com.facebook.katana.ProxyAuthDialog':
    print 'Logging in'
    # Because the Facebook authorization dialog is primarily a
    # WebView, we must click on x, y coordinates of the Continue
    # button instead of looking at the hierarchy.
    device.shell('input tap ' + str(int(.5 * MAX_X)) + ' ' +
                 str(int(.82 * MAX_Y)))
    perform_vc_dump(vc)
    activity_str = obtain_focus_and_allow_permissions(device, vc)

    # Authorize app to post to Facebook (or any other action).
    num_taps = 0
    while 'ProxyAuthDialog' in activity_str and num_taps < MAX_FB_AUTH_TAPS:
      print 'Facebook authorization #' + str(num_taps)
      device.shell('input tap ' + str(int(.90 * MAX_X)) + ' ' +
                   str(int(.95 * MAX_Y)))
      num_taps += 1
      time.sleep(3)
      activity_str = obtain_focus_and_allow_permissions(device, vc)
    return True

  else:
    print 'Could not log into Facebook.'
    print activity_str + ' ' + str(obtain_frag_list(package_name, device))
    return False


def google_login(device, curr_layout, click, vc):
  """Log into Google by automating the authentication flow."""

  # TODO(afergan): Figure out if this fails or if the button doesn't lead to a
  # login.
  print 'Trying to log into Google.'

  curr_layout.clickable.remove(click)
  touch(device, click)
  time.sleep(4)
  # Make sure the new screen is loaded by waiting for the dump.
  vc_dump = perform_vc_dump(vc)
  if not vc_dump:
    return False

  # Some apps want to access contacts to get user information.
  activity_str = obtain_focus_and_allow_permissions(device, vc)

  print activity_str
  if 'com.google.android.gms' not in activity_str:
    return False

  print 'Logging into G+'
  # Some apps ask to pick the Google user before logging in.
  if 'AccountChipAccountPickerActivity' in activity_str:
    print 'Selecting user.'
    v = vc.findViewById('id/account_profile_picture')
    if v:
      touch(device, v)
      print 'Selected user.'
      time.sleep(4)
      perform_vc_dump(vc)
    activity_str = obtain_focus_and_allow_permissions(device, vc)
    print activity_str
  if 'GrantCredentialsWithAclActivity' in activity_str:
    print 'Granting credentials.'
    perform_vc_dump(vc)
    v = vc.findViewById('id/accept_button')
    if v:
      print 'Granting'
      touch(device, v)
      time.sleep(4)

  return True


def return_to_app_activity(package_name, device, vc):
  """Tries to press back a number of times to return to the app."""

  # Returns the name of the activity, or EXITED_APP if it could not return.
  for press_num in range(0, NUM_BACK_PRESSES):
    perform_press_back(device)
    activity = obtain_activity_name(package_name, device, vc)
    if activity != EXITED_APP:
      print 'Returned to app'
      return activity

    time.sleep(5)
    print 'Failed returning to app, attempt #' + str(press_num + 1)

  return EXITED_APP


def obtain_focused_activity(device, vc):
  """Returns the activity ."""

  # The current focus returns a string in the format
  # mCurrentFocus=Window{35f66c3 u0 com.google.zagat/com.google.android.apps.
  # zagat.activities.BrowseListsActivity}
  # We only want the text between the backslash and the closing bracket.
  activity_str = obtain_focus_and_allow_permissions(device, vc)

  if not activity_str:
    return ''

  return extract_between(activity_str, '/', '}', -1)


def obtain_focus_and_allow_permissions(device, vc):
  """Accepts any permission prompts and returns the current focus."""
  activity_str = device.shell("dumpsys window windows "
                              "| grep -E 'mCurrentFocus'")

  # If the app is prompting for permissions, automatically accept them.
  while 'com.android.packageinstaller' in activity_str:
    print 'Allowing a permission.'
    perform_vc_dump(vc)
    touch(device, vc.findViewById('id/permission_allow_button'))
    time.sleep(2)
    activity_str = device.shell("dumpsys window windows "
                                "| grep -E 'mCurrentFocus'")

  # Keycodes are from
  # https://developer.android.com/reference/android/view/KeyEvent.html

  # If a physical device is at the lockscreen, unlock it.
  if 'StatusBar' in activity_str:
    # If the screen is off, turn it on.
    if (device.shell("dumpsys power | grep 'Display Power: state=' | grep -oE "
                     "'(ON|OFF)'") == 'OFF'):
      device.press('KEYCODE_POWER')
    # Unlock device.
    device.press('KEYCODE_MENU')
    activity_str = device.shell("dumpsys window windows "
                                "| grep -E 'mCurrentFocus'")
  return activity_str


def obtain_activity_name(package_name, device, vc):
  """Gets the current running activity of the package."""

  activity_str = obtain_focus_and_allow_permissions(device, vc)

  # If a popup menu has captured the focus, the focus will be in the format
  # mCurrentFocus=Window{8f1328e u0 PopupWindow:53a5957}
  if 'PopupWindow' in activity_str:
    popup_str = extract_between(activity_str, 'PopupWindow', '}')
    return 'PopupWindow' + popup_str.replace(':', '')

  if package_name in activity_str:
    # The current focus returns a string in the format
    # mCurrentFocus=Window{35f66c3 u0 com.google.zagat/com.google.android.apps.
    # zagat.activities.BrowseListsActivity}
    # We only want the text between the final period and the closing bracket.
    return extract_between(activity_str, '.', '}', -1)

  print 'Not in package. Current activity string is ' + activity_str
  return EXITED_APP


def obtain_frag_list(package_name, device):
  """Gets the list of fragments in the current layout."""
  activity_dump = device.shell('dumpsys activity ' + package_name)
  frag_dump = re.findall('Added Fragments:(.*?)FragmentManager', activity_dump,
                         re.DOTALL)
  if frag_dump:
    frag_list = re.findall(': (.*?){', frag_dump[0], re.DOTALL)
    # For irregular or app-generated fragment names with spaces and IDs,
    # terminate the name at the first space.
    for i in range(0, len(frag_list)):
      if ' ' in frag_list[i]:
        frag_list[i] = frag_list[i].split()[0]
    return frag_list

  return []


def obtain_package_name(device, vc):
  """Gets the package name of the current focused window."""

  activity_str = obtain_focus_and_allow_permissions(device, vc)

  # The current focus returns a string in the format
  # mCurrentFocus=Window{35f66c3 u0 com.google.zagat/com.google.android.apps.
  # zagat.activities.BrowseListsActivity}
  # We want the text before the backslash
  pkg_name = extract_between(activity_str, ' ', '/', -1)
  print 'Package name is ' + pkg_name
  return pkg_name


def is_active_layout(stored_layout, package_name, device, vc):
  """Check if the current Layout name matches a stored Layout."""
  print str(obtain_frag_list(package_name, device))
  print ('Curr activity / frag list: ' +
         obtain_activity_name(package_name, device, vc) + ' ' +
         str(obtain_frag_list(package_name, device)))
  print ('Stored activity + frag list: ' + stored_layout.activity + ' ' +
         str(stored_layout.frag_list))
  return (obtain_activity_name(package_name, device, vc) ==
          stored_layout.activity and Counter(obtain_frag_list(package_name,
                                                              device)) ==
          Counter(stored_layout.frag_list))


def save_layout_data(package_name, device, activity, frag_list, vc_dump):
  """Stores the view hierarchy and screenshots with unique filenames."""
  # Returns the path to the screenshot and the file number.

  if frag_list:
    first_frag = frag_list[0]
  else:
    first_frag = 'NoFrags'
  directory = (os.path.dirname(os.path.abspath(__file__)) + '/data/' +
               package_name)
  if not os.path.exists(directory):
    os.makedirs(directory)
  file_num = 0
  dump_file = os.path.join(directory, activity + '-' + first_frag + '-' +
                           str(file_num) + '.json')
  while os.path.exists(dump_file):
    file_num += 1
    dump_file = os.path.join(directory, activity + '-' + first_frag + '-' +
                             str(file_num) + '.json')

  layout_info = {}
  layout_info['hierarchy'] = {}
  layout_info['fragmentList'] = frag_list

  for view in vc_dump:
    # Because the children and parent are each instances, they are not JSON
    # serializable. We replace them with just the ids of the instances (and
    # discard the device info).
    dict_copy = copy.copy(view.__dict__)
    del dict_copy['device']
    if dict_copy['parent']:
      dict_copy['parent'] = dict_copy['parent'].getUniqueId()
    dict_copy['children'] = []
    for child in view.__dict__['children']:
      dict_copy['children'].append(child.getUniqueId())
    layout_info['hierarchy'][view.getUniqueId()] = dict_copy

  with open(dump_file, 'w') as out_file:
    try:
      json.dump(layout_info, out_file, indent=2)
    except TypeError:
      print 'Non-JSON serializable object in Layout.'

  screen_name = activity + '-' + first_frag + '-' + str(file_num) + '.png'
  screen_path = os.path.join(directory, screen_name)
  # device.shell() does not work for taking/pulling screencaps.
  device.shell('screencap /sdcard/' + screen_name)
  subprocess.call([ADB_PATH, '-s', SERIAL_NO, 'pull', '/sdcard/' + screen_name,
                   screen_path])
  device.shell('rm /sdcard/' + screen_name)
  # Returns the filename & num so that the screenshot can be accessed
  # programatically.
  return screen_path, file_num


def save_ui_flow_relationships(layout_to_save, package_name):
  """Dumps to file the click dictionary and preceding Layouts."""
  directory = (os.path.dirname(os.path.abspath(__file__)) + '/data/' +
               package_name)
  click_file = os.path.join(directory, layout_to_save.get_name() +
                            '-clicks.json')
  click_info = {}
  click_info['click_dict'] = layout_to_save.click_dict
  click_info['preceding'] = layout_to_save.preceding
  click_info['depth'] = layout_to_save.depth
  with open(click_file, 'w') as out_file:
    json.dump(click_info, out_file, indent=2)


def find_layout_in_map(activity, frag_list, vc_dump, layout_map):
  """Finds the  current Layout in the layout array (empty if new Layout)."""
  # TODO(afergan): Consider creating another map indexed by the values compared
  # in is_duplicate so that this comparison is O(1).
  for val in layout_map.values():
    if val.is_duplicate(activity, frag_list, vc_dump):
      return val
  return None


def create_layout(package_name, device, vc_dump, activity, frag_list):
  """Stores the current layout in the Layout data structure."""
  screenshot, num = save_layout_data(package_name, device, activity, frag_list,
                                     vc_dump)

  # If we think the first element in the view hierarchy is a back button, move
  # it to the end of the list so that we click on it last.
  if 'back' in vc_dump[0].getUniqueId().lower():
    vc_dump.append(vc_dump.pop())

  l = Layout(activity, frag_list, vc_dump, screenshot, num)

  for view in l.hierarchy:
    try:
      if (view.isClickable() and view.getVisibility() == VISIBLE and
          is_in_bounds(view.getX(), view.getY()) and view.getWidth() > 0 and
          view.getHeight() > 0):
        if view.getText():
          print (view.getId() + ' ' + view.getClass() + ' ' +
                 str(view.getXY()) + ' ' + view.getText() +
                 '-- will be clicked')
        else:
          print (view.getId() + ' ' + view.getClass() + ' ' +
                 str(view.getXY()) + '-- will be clicked')
        l.clickable.append(view)
    except AttributeError:
      print 'Could not get view attributes.'

  # For views that cancel or bring us back, click on them last. However, do not
  # hold this against views with the unique id id/no_id/##.
  for clickview in l.clickable:
    clickstr = ''
    if 'no_id' in clickview.getUniqueId().lower():
      clickstr = ''
    else:
      clickstr = clickview.getUniqueId().lower()

    if clickview.getText():
      print 'Text: ' + clickview.getText()
      clickstr += ' ' + clickview.getText().lower()
    if any(x in clickstr for x in NEGATIVE_WORDS):
      print 'Going to the end of the list b/c of text or ID: ' + clickstr
      l.clickable.remove(clickview)
      l.clickable.append(clickview)

  return l


def link_ui_layouts(prev_layout, curr_layout, prev_clicked, package_name):
  """Stores the relationship between prev_layout and curr_layout."""

  # We store in the Layout information that the last layout links to the current
  # layout, and that the current layout can be reached from the last layout. We
  # use the id of the last clicked element as the dictionary key so that we know
  # which element leads from layout to layout.

  if prev_clicked:
    print 'Previous clicked: ' + prev_clicked
    prev_layout.click_dict[prev_clicked] = curr_layout.get_name()
    prev_name = prev_layout.get_name()
    if prev_name not in curr_layout.preceding:
      curr_layout.preceding.append(prev_name)
  else:
    print 'Lost track of last clicked!'
  print 'Prev layout: ' + prev_layout.get_name()
  print 'Curr layout: ' + curr_layout.get_name()
  if curr_layout.depth == -1 or curr_layout.depth > prev_layout.depth + 1:
    curr_layout.depth = prev_layout.depth + 1

  # TODO(afergan): Remove this later. For debugging, we print the clicks after
  # each click to a new layout is recorded. However, this results in a lot of
  # repeated writes to the same file. In the future, we can just write each
  # file once we're done crawling the app.
  save_ui_flow_relationships(prev_layout, package_name)
  save_ui_flow_relationships(curr_layout, package_name)


def obtain_curr_layout(activity, package_name, vc_dump, layout_map,
                       still_exploring, device):
  """Extracts UI info and return the current Layout."""

  # Gets the current UI info. If we have seen this UI before, return the
  # existing Layout. If not, create a new Layout and save it to the layout
  # array.

  frag_list = obtain_frag_list(package_name, device)
  layout = find_layout_in_map(activity, frag_list, vc_dump, layout_map)

  if layout:
    print 'Found duplicate'
    return layout
  else:
    print 'New layout'
    new_layout = create_layout(package_name, device, vc_dump, activity,
                               frag_list)
    # Make sure we have a valid Layout. This will be false if we get a socket
    # timeout.
    if new_layout.get_name():
      layout_map[new_layout.get_name()] = new_layout
      # If there are clickable views, explore this new Layout.
      if new_layout.clickable:
        still_exploring[new_layout.get_name()] = new_layout
        print ('Added ' + new_layout.get_name() + ' to still_exploring. Length '
               'is now ' + str(len(still_exploring)))
      return new_layout

  print 'Could not obtain current layout.'
  return None


def find_view_to_lead_to_layout(layout1, layout2):
  """Given 2 Layouts, return the view of layout 1 that leads to layout 2."""

  try:
    return layout1.click_dict.keys()[layout1.click_dict.values().index(
        layout2.get_name())]
  except ValueError:
    print '*** Could not find a view to link to the succeeding Layout!'
    print (str(layout1.click_dict) + ' does not have a path to ' +
           layout2.get_name())
  return FAILED_FINDING_NAME


def find_shortest_path(graph, start, end, prevpath=()):
  """Use BFS to find the shortest path from the start to end node."""

  # Modified from http://stackoverflow.com/a/8922151/1076508 to prevent cycles
  # and account for already visited nodes.

  queue = [[start]]
  visited = set(prevpath)

  while queue:
    path = queue.pop(0)
    node = path[-1]
    # Path found.
    if node == end:
      return path
    # Enumerate all adjacent nodes, construct a new path and push it into the
    # queue.
    for adjacent in graph.get(node, []):
      if adjacent not in visited:
        new_path = list(path)
        new_path.append(adjacent)
        queue.append(new_path)
        visited.add(adjacent)


def follow_path_to_layout(path, goal, package_name, device, layout_map,
                          layout_graph, still_exploring, vc):
  """Attempt to follow path all the way to the desired layout."""

  # We need to look at the length of path for each iteration since the path can
  # change when we get off course.
  i = 0
  while i < len(path) - 1:
    # We can be lenient here and only evaluate if the activity and fragments are
    # the same (and allow the layout hierarchy to have changed a little bit),
    # since we then evaluate if the clickable view we want is in the Layout.
    p = path[i]
    p_layout = layout_map.get(p)
    if is_active_layout(p_layout, package_name, device, vc):
      print 'Got to ' + p
      click_id = find_view_to_lead_to_layout(p_layout,
                                             layout_map.get(path[i+1]))
      if i > 0 and (layout_map.get(path[i-1]).depth + 1 <
                    layout_map.get(path[i]).depth):
        layout_map.get(path[i]).depth = layout_map.get(path[i-1]).depth + 1

      if click_id == FAILED_FINDING_NAME:
        print ('Could not find the right view to click on, was looking for ' +
               click_id)
        return False
      if click_id == BACK_BUTTON:
        perform_press_back(device)
      else:
        vc_dump = perform_vc_dump(vc)
        if vc_dump:
          click_target = next((view for view in vc_dump
                               if view.getUniqueId() == click_id), None)
          if click_target:
            prev_clicked = click_target.getUniqueId()
            touch(device, click_target)
        else:
          return False
    else:
      print 'Toto, I\'ve a feeling we\'re not on the right path anymore.'
      # Remove the edge from the graph so that we don't follow it again (but
      # don't remove it from our data collection.
      try:
        layout_graph[p].remove(path[i+1])
        print 'Removed edge from ' + p + ' to ' + path[i+1]
      except KeyError:
        print ('??? Could not find edge from ' + p + ' to ' + path[i+1] +
               ' to remove from graph.')

      # Figure out where we are & link it to the previous layout, but then try
      # to still get to the intended Layout.
      activity = obtain_activity_name(package_name, device, vc)

      if activity is EXITED_APP:
        activity = return_to_app_activity(package_name, device, vc)

      vc_dump = perform_vc_dump(vc)
      curr_layout = obtain_curr_layout(activity, package_name, vc_dump,
                                       layout_map, still_exploring, device)

      prev_layout = layout_map.get(p)
      path_to_curr = path[:i]

      if not prev_layout.is_duplicate_layout(curr_layout):
        link_ui_layouts(prev_layout, curr_layout, prev_clicked, package_name)
        path_to_curr.append(curr_layout.get_name())

      new_path = find_shortest_path(layout_graph, curr_layout.get_name(),
                                    goal.get_name(), path_to_curr)
      if new_path:
        print 'Back on track -- found new route to ' + goal.get_name()
        path += new_path
      else:
        print 'Stopping here. Could not find a way to ' + goal.get_name()
        return

    i += 1

  # We made it all the way through!
  if i == len(path) - 1:
    print 'Got to end of path.'
    if layout_map.get(path[i-1]).depth + 1 < layout_map.get(path[i]).depth:
      layout_map.get(path[i]).depth = layout_map.get(path[i-1]).depth + 1
    # Make sure that we end up at the Layout that we want.
    return is_active_layout(goal, package_name, device, vc)


def crawl_until_exit(vc, device, package_name, layout_map, layout_graph,
                     still_exploring, start_layout, logged_in, config_data):
  """Main crawler loop. Evaluates layouts, stores new data, and clicks views."""

  print 'Logged in: ' + str(logged_in)
  curr_layout = start_layout
  prev_clicked = ''
  consec_back_presses = 0

  while (len(layout_map) < MAX_LAYOUTS and
         consec_back_presses < MAX_CONSEC_BACK_PRESSES):

    if device.isKeyboardShown():
      perform_press_back(device)

    activity = obtain_activity_name(package_name, device, vc)

    if activity is EXITED_APP:
      activity = return_to_app_activity(package_name, device, vc)
      if activity is EXITED_APP:
        print 'Current layout is not app and we cannot return'
        break
      else:
        prev_clicked = BACK_BUTTON

    prev_layout = curr_layout
    vc_dump = perform_vc_dump(vc)
    if vc_dump:
      curr_layout = obtain_curr_layout(activity, package_name, vc_dump,
                                       layout_map, still_exploring, device)
      print 'Curr layout: ' + curr_layout.get_name()
      if not prev_layout.is_duplicate_layout(curr_layout):
        print 'At a diff layout!'
        link_ui_layouts(prev_layout, curr_layout, prev_clicked, package_name)
        prev_name = prev_layout.get_name()
        if prev_name in layout_graph:
          print 'New set: ' + prev_name + ' ' + curr_layout.get_name()
          layout_graph.get(prev_name).add(curr_layout.get_name())
        else:
          layout_graph[prev_name] = {curr_layout.get_name()}
          print 'Adding to set: ' + prev_name + ' ' + curr_layout.get_name()
          print 'Num of nodes in layout graph: ' + str(len(layout_graph))

      print 'Layout depth: ' + str(curr_layout.depth)
      print 'Num clickable: ' + str(len(curr_layout.clickable))

      if curr_layout.clickable:
        found_login = False
        if not logged_in:
          for click in curr_layout.clickable:
            clickid = click.getUniqueId().lower()
            if click.getText():
              clicktext = click.getText().lower()
            else:
              clicktext = ''
            if (click.getClass() == 'com.facebook.widget.LoginButton'
                or any('facebook' in x for x in [clickid, clicktext])
                or ('fb' in clickid and any(s in clickid for s in
                                            ['login', 'log_in', 'signin',
                                             'sign_in']))):
              found_login = True
              consec_back_presses = 0
              prev_clicked = click.getUniqueId()
              logged_in = fb_login(package_name, device, curr_layout, click, vc)

            elif (click.getClass ==
                  'com.google.android.gms.common.SignInButton' or
                  any('google' in x for x in [clickid, clicktext]) or
                  any('gplus' in x for x in [clickid, clicktext]) or
                  clickid == 'sign_in_button'):
              found_login = True
              consec_back_presses = 0
              prev_clicked = click.getUniqueId()
              logged_in = google_login(device, curr_layout, click, vc)

        if not found_login:
          c = curr_layout.clickable[0]
          touch(device, c)
          consec_back_presses = 0
          prev_clicked = c.getUniqueId()
          curr_layout.clickable.remove(c)
          if device.isKeyboardShown():
            use_keyboard(prev_clicked, config_data, device, vc)

      else:
        print 'Removing ' + curr_layout.get_name() + ' from still_exploring.'
        still_exploring.pop(curr_layout.get_name(), 0)
        consec_back_presses += 1
        print ('Clicking back button, consec_back_presses is ' +
               str(consec_back_presses))
        perform_press_back(device)
        prev_layout = curr_layout
        prev_clicked = BACK_BUTTON

        # Make sure we have changed layouts.
        vc_dump = perform_vc_dump(vc)
        num_dumps = 0
        while not vc_dump and num_dumps < MAX_DUMPS:
          perform_press_back(device)
          consec_back_presses += 1
          vc_dump = perform_vc_dump(vc)
          num_dumps += 1

        if num_dumps == MAX_DUMPS:
          print 'Could not get a ViewClient dump.'
          break

        activity = obtain_activity_name(package_name, device, vc)
        if activity is EXITED_APP:
          activity = return_to_app_activity(package_name, device, vc)
          if activity is EXITED_APP:
            print 'Clicking back took us out of the app.'
            break

        if vc_dump:
          curr_layout = obtain_curr_layout(activity, package_name, vc_dump,
                                           layout_map, still_exploring, device)
          if prev_layout.is_duplicate_layout(curr_layout):
            # We have nothing left to click, and the back button doesn't change
            # layouts.
            print 'Pressing back keeps at the current layout.'
            break
          else:
            link_ui_layouts(prev_layout, curr_layout, 'back button',
                            package_name)
    else:
      perform_press_back(device)
      consec_back_presses += 1

  return logged_in


def crawl_package(vc, device, serialno, package_name=None):
  """Crawl package. Explore blindly, then return to unexplored layouts."""

  global SERIAL_NO
  SERIAL_NO = serialno

  set_device_dimens(vc, device)
  # Layout map stores all Layouts that we have seen, while the still_exploring
  # consists of only Layouts that have not been exhaustively explored yet (or
  # found to be unreachable.) The Layout graph stores all of the connections
  # between different screens.
  layout_map = {}
  still_exploring = {}
  layout_graph = {}

  config_data = Config().data

  # Stores if we have logged in during this crawl/session. If the app has
  # previously logged into an app or service (and can skip the authorization
  # process), we will be unable to detect that.
  # TODO(afergan): Is there a way to determine if we've already authorized a
  # media service? Clicking on Facebook once we've already authorized it just
  # pops up a momentary dialog then goes to the next screen, so it would be
  # difficult to differentiate an authorized login from a normal button that
  # happened to be named "facebook_login" or a failed login.
  logged_in = False

  if not package_name:
    package_name = obtain_package_name(device, vc)

  activity = obtain_activity_name(package_name, device, vc)
  if activity == EXITED_APP:
    return
  vc_dump = perform_vc_dump(vc)
  if not vc_dump:
    return

  first_layout = obtain_curr_layout(activity, package_name, vc_dump, layout_map,
                                    still_exploring, device)
  first_layout.depth = 0

  print 'Root is ' + first_layout.get_name()
  num_crawls = 0

  logged_in = crawl_until_exit(vc, device, package_name, layout_map,
                               layout_graph, still_exploring, first_layout,
                               logged_in, config_data)

  # Recrawl Layouts that aren't completely explored.
  while (still_exploring and num_crawls < MAX_CRAWLS and
         len(layout_map) < MAX_LAYOUTS):
    print 'Crawl #' + str(num_crawls)
    num_crawls += 1
    print 'We have seen ' + str(len(layout_map)) + ' unique layouts.'
    print 'We still have ' + str(len(still_exploring)) + ' layouts to explore.'
    print 'Still need to explore: ' + str(still_exploring.keys())
    l = still_exploring.values()[0]
    print 'Now trying to explore '+  l.get_name()

    # Restart the app with its initial screen.
    device.shell('am force-stop ' + package_name)
    device.shell('monkey -p ' + package_name +
                 ' -c android.intent.category.LAUNCHER 1')

    time.sleep(5)

    activity = obtain_activity_name(package_name, device, vc)
    if activity == EXITED_APP:
      print 'Could not launch app.'
      return

    starting_layout = obtain_curr_layout(activity, package_name, vc_dump,
                                         layout_map, still_exploring, device)
    starting_layout.depth = 0
    path = find_shortest_path(layout_graph, starting_layout.get_name(),
                              l.get_name())
    if path:
      print ('Shortest path from ' + starting_layout.get_name() + ' to ' +
             l.get_name() + ': ' + str(path))

      reached_layout = follow_path_to_layout(path, l, package_name, device,
                                             layout_map, layout_graph,
                                             still_exploring, vc)
      if reached_layout:
        print 'Reached the layout we were looking for.'
      else:
        print ('Did not reach intended layout, removing ' + l.get_name() +
               ' from still_exploring.')
        still_exploring.pop(l.get_name(), 0)
      activity = obtain_activity_name(package_name, device, vc)
    else:
      print 'No path to ' + l.get_name() + '. Removing from still_exploring.'
      still_exploring.pop(l.get_name(), 0)

    if activity != EXITED_APP:

      vc_dump = perform_vc_dump(vc)

      if vc_dump:
        curr_layout = obtain_curr_layout(activity, package_name, vc_dump,
                                         layout_map, still_exploring, device)
        print 'Wanted ' + l.get_name() + ', at ' + curr_layout.get_name()

        if curr_layout.clickable:
          # If we made it to our intended Layout, or at least a Layout with
          # unexplored views, start crawling again.
          print 'Crawling again'
          logged_in = crawl_until_exit(vc, device, package_name, layout_map,
                                       layout_graph, still_exploring,
                                       curr_layout, logged_in, config_data)
          print ('Done with the crawl. Still ' + str(len(l.clickable)) +
                 ' views to click for this Layout.')
        else:
          print 'Nothing left to click for ' + l.get_name()
          still_exploring.pop(l.get_name(), 0)

  print 'No more layouts to crawl.'
