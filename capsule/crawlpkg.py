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


def extract_between(text, sub1, sub2, nth=1):
  """Extracts a substring from text between two given substrings."""
  # Credit to
  # https://www.daniweb.com/programming/software-development/code/446964/extract-a-string-between-2-substrings-python-

  # Prevent sub2 from being ignored if it's not there.
  if sub2 not in text.split(sub1, nth)[-1]:
    return None
  return text.split(sub1, nth)[-1].split(sub2, nth)[0]


def set_device_dimens(vc, device):
  """Sets global variables to the dimensions of the device."""
  global MAX_X, MAX_Y, STATUS_BAR_HEIGHT

  # Returns a string similar to "Physical size: 1440x2560"
  size = device.shell('wm size')
  # Returns a string similar to "Physical density: 560"
  density = int(device.shell('wm density').split(' ')[-1])
  # We do not want the crawler to click on the navigation bar because it can
  # hit the back button or minimize the app.
  # From https://developer.android.com/guide/practices/screens_support.html
  # The conversion of dp units to screen pixels is simple: px = dp * (dpi / 160)
  navbar_height = NAVBAR_DP_HEIGHT * density / 160

  MAX_X = int(extract_between(size, ': ', 'x'))
  MAX_Y = int(extract_between(size, 'x', '\r')) - navbar_height
  vc_dump = perform_vc_dump(vc)
  if vc_dump:
    STATUS_BAR_HEIGHT = (
        vc_dump[0].getY() - int(vc_dump[0]['layout:getLocationOnScreen_y()']))
  else:
    # Keep status at default 0 height.
    print 'Cannot get status bar height.'


def perform_press_back(device):
  device.press('KEYCODE_BACK')


def perform_vc_dump(vc):
  try:
    return vc.dump(window='-1')
  except IOError:
    print '*** Socket timeout!'
    return None


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


def obtain_focus_and_allow_permissions(device, vc):
  """Accepts any permission prompts and returns the current focus."""
  activity_str = device.shell('dumpsys window windows '
                              '| grep -E \'mCurrentFocus\'')

  # If the app is prompting for permissions, automatically accept them.
  while 'com.android.packageinstaller' in activity_str:
    print 'Allowing a permission.'
    perform_vc_dump(vc)
    vc.findViewById('id/permission_allow_button').touch()
    time.sleep(2)
    activity_str = device.shell('dumpsys window windows '
                                '| grep -E \'mCurrentFocus\'')

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


def save_layout_data(package_name, activity, frag_list, vc_dump):
  """Stores the view hierarchy and screenshots with unique filenames."""
  # Returns the path to the screenshot and the file number.

  if frag_list:
    first_frag = frag_list[0]
  else:
    first_frag = 'NoFrags'

  directory = (
      os.path.dirname(os.path.abspath(__file__)) + '/data/' + package_name)
  if not os.path.exists(directory):
    os.makedirs(directory)
  file_num = 0
  dump_file = os.path.join(
      directory, activity + '-' + first_frag + '-' + str(file_num) + '.json')
  while os.path.exists(dump_file):
    file_num += 1
    dump_file = os.path.join(
        directory,
        activity + '-' + first_frag + '-' + str(file_num) + '.json')

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
    json.dump(layout_info, out_file, indent=2)

  screen_name = activity + '-' + first_frag + '-' + str(file_num) + '.png'
  screen_path = os.path.join(directory, screen_name)
  # device.shell() does not work for taking/pulling screencaps.
  subprocess.call([ADB_PATH, 'shell', 'screencap', '/sdcard/' + screen_name])
  subprocess.call([ADB_PATH, 'pull', '/sdcard/' + screen_name, screen_path])
  subprocess.call([ADB_PATH, 'shell', 'rm', '/sdcard/' + screen_name])
  # Returns the filename & num so that the screenshot can be accessed
  # programatically.
  return screen_path, file_num


def save_ui_flow_relationships(layout_to_save, package_name):
  """Dumps to file the click dictionary and preceding Layouts."""
  directory = (
      os.path.dirname(os.path.abspath(__file__)) + '/data/' + package_name)
  click_file = os.path.join(directory, layout_to_save.get_name() +
                            '-clicks.json')
  click_info = {}
  click_info['click_dict'] = layout_to_save.click_dict
  click_info['preceding'] = layout_to_save.preceding
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


def create_layout(package_name, vc_dump, activity, frag_list):
  """Stores the current layout in the Layout data structure."""
  screenshot, num = save_layout_data(package_name, activity, frag_list, vc_dump)

  # If we think the first element in the view hierarchy is a back button, move
  # it to the end of the list so that we click on it last.
  if 'back' in vc_dump[0].getUniqueId().lower():
    vc_dump.append(vc_dump.pop())

  l = Layout(activity, frag_list, vc_dump, screenshot, num)

  for view in l.hierarchy:
    # TODO(afergan): For now, only click on certain views, and allow custom
    # views. Evaluate later if this is worth it or if we should just click
    # on everything attributed as clickable.
    try:
      if (view.isClickable() and view.getVisibility() == VISIBLE and
          view.getX() >= 0 and view.getX() <= MAX_X and
          view.getWidth() > 0 and
          view.getY() >= STATUS_BAR_HEIGHT and view.getY() <= MAX_Y
          and view.getHeight() > 0):
        print (view.getId() + ' ' + view.getClass()
               + ' ' + str(view.getXY()) + '-- will be clicked')
        l.clickable.append(view)
    except AttributeError:
      print 'Could not get view attributes.'
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
    curr_layout.preceding.append(prev_layout.get_name())
  else:
    print 'Lost track of last clicked!'

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
    new_layout = create_layout(package_name, vc_dump, activity, frag_list)
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

  return FAILED_FINDING_NAME


def find_path_from_root_to_layout(layout, layout_map):
  """Given a Layout, finds the path of UI elements to that Layout."""

  path = []
  curr_path_layout = layout
  # If there is a splash screen or intro screen that is stored, we could have
  # multiple Layouts that do not have preceding Layouts.

  while curr_path_layout.preceding:
    print 'Looking for path from ' + layout.get_name()
    path_layouts = [p[0] for p in path]
    succeeding_layout = curr_path_layout
    # TODO(afergan): Using the first element in preceding doesn't ensure
    # shortest path. Is it worth keeping track of the depth of every Layout to
    # create the shortest path?
    curr_path_layout = None
    for pre in succeeding_layout.preceding:
      if pre not in path_layouts:
        curr_path_layout = layout_map.get(pre)
        break
      else:
        return path

    view = find_view_to_lead_to_layout(curr_path_layout, succeeding_layout)

    # This should not happen since if we store the predecessor of one Layout, we
    # also store which view of the predecessor leads to that Layout. However,
    # if it does, we can try exploring other preceding layouts
    if view == FAILED_FINDING_NAME:
      return []
    else:
      print ('Inserting ' + view + ', ' + curr_path_layout.get_name()
             + ' to path')
      path.insert(0, (curr_path_layout.get_name(), view))

  return path


def follow_path_to_layout(path, goal, package_name, device, layout_map,
                          still_exploring, vc):
  """Attempt to follow path all the way to the desired layout."""
  if not path:
    return is_active_layout(layout_map.values()[0], package_name, device, vc)

  for p in path:
    # We can be lenient here and only evaluate if the activity and fragments are
    # the same (and allow the layout hierarchy to have changed a little bit),
    # since we then evaluate if the clickable view we want is in the Layout.
    if not is_active_layout(layout_map.get(p[0]), package_name, device, vc):
      print 'Toto, I\'ve a feeling we\'re not on the right path anymore.'
      p_idx = path.index(p)
      if p_idx > 0:
        activity = obtain_activity_name(package_name, device, vc)

        if activity is EXITED_APP:
          return False
        vc_dump = perform_vc_dump(vc)
        curr_layout = obtain_curr_layout(activity, package_name, vc_dump,
                                         layout_map, still_exploring, device)
        prev_layout = layout_map.get(path[p_idx - 1][0])
        prev_clicked = layout_map.get(path[p_idx - 1][1])
        link_ui_layouts(prev_layout, curr_layout, prev_clicked, package_name)

      return False

    click_id = p[1]
    if click_id == BACK_BUTTON:
      perform_press_back(device)
    else:
      vc_dump = perform_vc_dump(vc)
      if vc_dump:
        click_target = next((view for view in vc_dump
                             if view.getUniqueId() == click_id), None)
        if click_target:
          print 'Clicking on ' + click_target.getUniqueId()
          device.touch(click_target.getX(), click_target.getY())
      else:
        print ('Could not find the right view to click on, was looking '
               'for ' + click_id)
        return False

  # Make sure that we end up at the Layout that we want.
  return is_active_layout(goal, package_name, device, vc)


def crawl_until_exit(vc, device, package_name, layout_map, still_exploring,
                     start_layout, logged_in):
  """Main crawler loop. Evaluates layouts, stores new data, and clicks views."""
  print 'Logged in: ' + str(logged_in)
  curr_layout = start_layout
  prev_clicked = ''
  consec_back_presses = 0

  while (len(layout_map) < MAX_LAYOUTS and
         consec_back_presses < MAX_CONSEC_BACK_PRESSES):

    # If last click opened the keyboard, assume we're in the same layout and
    # just click on the next element. Since opening the keyboard can leave
    # traces of additional views, don't check if layout is duplicate.
    # TODO(afergan): Is this a safe assumption?
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

      print 'Num clickable: ' + str(len(curr_layout.clickable))

      if curr_layout.clickable:
        try:
          found_login = False
          if not logged_in:
            for click in curr_layout.clickable:
              click_id = click.getUniqueId().lower()
              if (click.getClass() == 'com.facebook.widget.LoginButton' or
                  ('facebook' in click_id) or ('fb' in click_id and
                                               any(s in click_id for s in
                                                   ['login', 'log_in', 'signin',
                                                    'sign_in']))):
                found_login = True
                print 'Trying to log into Facebook.'
                # Sometimes .touch() doesn't work
                device.shell('input tap ' + str(click.getX()) +
                             ' ' + str(click.getY()))
                consec_back_presses = 0
                prev_clicked = click.getUniqueId()
                curr_layout.clickable.remove(click)
                time.sleep(10)
                # Make sure the new screen is loaded by waiting for the dump.
                perform_vc_dump(vc)
                activity_str = obtain_focus_and_allow_permissions(device, vc)
                print activity_str
                if 'com.facebook.katana' in activity_str:
                  logged_in = True
                  # Because the Facebook authorization dialog is primarily a
                  # WebView, we must click on x, y coordinates of the Continue
                  # button instead of looking at the hierarchy.
                  device.shell('input tap ' + str(int(.5 * MAX_X)) + ' ' +
                               str(int(.82 * MAX_Y)))
                  consec_back_presses = 0
                  perform_vc_dump(vc)
                  activity_str = obtain_focus_and_allow_permissions(device, vc)

                  # Authorize app to post to Facebook (or any other action).
                  num_taps = 0
                  while ('ProxyAuthDialog' in activity_str and
                         num_taps < MAX_FB_AUTH_TAPS):
                    print 'Facebook authorization #' + str(num_taps)
                    device.shell('input tap ' + str(int(.90 * MAX_X)) + ' ' +
                                 str(int(.95 * MAX_Y)))
                    num_taps += 1
                    time.sleep(3)
                    activity_str = obtain_focus_and_allow_permissions(
                        device, vc)

                else:
                  print 'Could not log into Facebook.'
                  print (activity_str + ' ' +
                         str(obtain_frag_list(package_name, device)))
              elif (('gplus' in click_id or 'google' in click_id) and
                    any(s in click_id for s in ['login', 'log_in', 'signin',
                                                'sign_in'])):
                found_login = True
                print 'Trying to log into Google+.'
                device.touch(str(click.getX()), str(click.getY()))
                consec_back_presses = 0
                prev_clicked = click.getUniqueId()
                curr_layout.clickable.remove(click)
                time.sleep(4)
                # Make sure the new screen is loaded by waiting for the dump.
                perform_vc_dump(vc)

                # Some apps want to access contacts to get user information.
                activity_str = obtain_focus_and_allow_permissions(device, vc)

                print activity_str
                if 'com.google.android.gms' in activity_str:
                  print 'Logging into G+'
                  # Some apps ask to pick the Google user before logging in.
                  if 'AccountChipAccountPickerActivity' in activity_str:
                    print 'Selecting user.'
                    v = vc.findViewById('id/account_profile_picture')
                    if v:
                      device.touch(v.getX(), v.getY())
                      print 'selected user.'
                      time.sleep(4)
                      perform_vc_dump(vc)
                    activity_str = obtain_focus_and_allow_permissions(
                        device, vc)
                    print activity_str
                  if 'GrantCredentialsWithAclActivity' in activity_str:
                    print 'Granting credentials.'
                    perform_vc_dump(vc)
                    v = vc.findViewById('id/accept_button')
                    if v:
                      print 'granting'
                      device.touch(v.getX(), v.getY())
                      time.sleep(4)

          if not found_login:
            c = curr_layout.clickable[0]
            print('Clicking {} {}, ({},{})'.format(c.getUniqueId(),
                                                   c.getClass(), c.getX(),
                                                   c.getY()))
            device.touch(c.getX(), c.getY())
            consec_back_presses = 0
            prev_clicked = c.getUniqueId()
            curr_layout.clickable.remove(c)
        except UnicodeEncodeError:
          print '***Unicode coordinates'
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
          break

        activity = obtain_activity_name(package_name, device, vc)
        if activity is EXITED_APP:
          activity = return_to_app_activity(package_name, device, vc)
          if activity is EXITED_APP:
            print 'Clicking back took us out of the app'
            break

        if vc_dump:
          curr_layout = obtain_curr_layout(activity, package_name, vc_dump,
                                           layout_map, still_exploring, device)
          if prev_layout.is_duplicate_layout(curr_layout):
            # We have nothing left to click, and the back button doesn't change
            # layouts.
            print 'Pressing back keeps at the current layout'
            return
          else:
            link_ui_layouts(prev_layout, curr_layout, 'back button',
                            package_name)
    else:
      perform_press_back(device)
      consec_back_presses += 1

  return logged_in


def crawl_package(vc, device, package_name=None):
  """Crawl package. Explore blindly, then return to unexplored layouts."""

  set_device_dimens(vc, device)
  # Layout map stores all Layouts that we have seen, while the still_exploring
  # consists of only Layouts that have not been exhaustively explored yet (or
  # found to be unreachable.)
  layout_map = {}
  still_exploring = {}

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

  # Store the root Layout
  print 'Storing root'
  vc_dump = perform_vc_dump(vc)
  if not vc_dump:
    return
  activity = obtain_activity_name(package_name, device, vc)
  if activity == EXITED_APP:
    return
  root_layout = obtain_curr_layout(activity, package_name, vc_dump, layout_map,
                                   still_exploring, device)
  logged_in = crawl_until_exit(vc, device, package_name, layout_map,
                               still_exploring, root_layout, logged_in)

  print 'Root is ' + root_layout.get_name()
  print 'We have seen ' + str(len(layout_map)) + ' unique layouts.'

  num_crawls = 0

  # Recrawl Layouts that aren't completely explored.
  while (still_exploring and num_crawls < MAX_CRAWLS and
         len(layout_map) < MAX_LAYOUTS):
    print 'Crawl #' + str(num_crawls)
    num_crawls += 1
    print 'We still have ' + str(len(still_exploring)) + ' layouts to explore.'
    print 'Still need to explore: ' + str(still_exploring.keys())
    l = still_exploring.values()[0]
    print 'Now trying to explore '+  l.get_name()
    path = find_path_from_root_to_layout(l, layout_map)
    print 'Route from root to ' + l.get_name()

    # Restart the app with its initial screen.
    subprocess.call([ADB_PATH, 'shell', 'am force-stop', package_name])
    subprocess.call([ADB_PATH, 'shell', 'monkey', '-p', package_name, '-c',
                     'android.intent.category.LAUNCHER', '1'])
    time.sleep(5)

    if path:
      for p in path:
        print p[0] + ' ' + p[1]
      reached_layout = follow_path_to_layout(path, l, package_name, device,
                                             layout_map, still_exploring, vc)
    else:
      reached_layout = is_active_layout(l, package_name, device, vc)
      if reached_layout:
        print 'At root layout: ' + str(reached_layout)
      else:
        print 'No path to ' + l.get_name()

    vc_dump = perform_vc_dump(vc)
    activity = obtain_activity_name(package_name, device, vc)

    if reached_layout:
      print 'Reached the layout we were looking for.'
    else:
      print ('Did not reach intended layout, removing ' + l.get_name() +
             ' from still_exploring.')
      still_exploring.pop(l.get_name(), 0)

    if activity == EXITED_APP:
      break

    if vc_dump:
      curr_layout = obtain_curr_layout(activity, package_name, vc_dump,
                                       layout_map, still_exploring, device)
      print 'Wanted ' + l.get_name() + ', at ' + curr_layout.get_name()

      if curr_layout.clickable:
        # If we made it to our intended Layout, or at least a Layout with
        # unexplored views, start crawling again.
        print 'Crawling again'
        logged_in = crawl_until_exit(vc, device, package_name, layout_map,
                                     still_exploring, curr_layout, logged_in)
        print ('Done with the crawl. Still ' + str(len(l.clickable)) +
               ' views to click for this Layout.')
      else:
        print 'Nothing left to click for ' + l.get_name()
        still_exploring.pop(l.get_name(), 0)

  print 'No more layouts to crawl'
