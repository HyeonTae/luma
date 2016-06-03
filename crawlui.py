"""A module for installing and crawling the UI of Android application."""

import os
import re
import subprocess

from view import View

# Linux ADB path
# ADB_PATH = os.path.expanduser('~') + '/Android/Sdk/platform-tools/adb'
# OS X ADB path
ADB_PATH = '/usr/local/bin/adb'

MAX_WIDTH = 1080
# TODO(afergan): For layouts longer than the width of the screen, scroll down
# and click on them. For now, we ignore them.
MAX_HEIGHT = 1920
NAVBAR_HEIGHT = 63

# Visibility
VISIBLE = 0x0
INVISIBLE = 0x4
GONE = 0x8

# Return a unique string if the package is not the focused window. Since
# activities cannot have spaces, we ensure that no activity will be named this.
EXITED_APP = 'exited app'

view_root = []
view_array = []


def perform_press_back():
  subprocess.call([ADB_PATH, 'shell', 'input', 'keyevent', '4'])


def get_activity_name(package_name):
  """Gets the current running activity of the package."""
  # TODO(afergan): See if we can consolidate this with get_fragment_list, but
  # still make sure that the current app has focus.

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


def save_screenshot(package_name, activity, frag_list):
  """Store the screenshot with a unique filename."""
  directory = (os.path.dirname(os.path.abspath(__file__)) + '/data/'
               + package_name)
  if not os.path.exists(directory):
    os.makedirs(directory)
  screenshot_num = 0
  while os.path.exists(directory + '/' + activity + '-' + frag_list[0] + '-' +
                       str(screenshot_num) + '.png'):
    screenshot_num += 1
  screen_name = activity + '-' + frag_list[0] + '-' + str(screenshot_num) + '.png'
  print screen_name
  screen_path = directory + '/' + screen_name
  subprocess.call([ADB_PATH, 'shell', 'screencap', '/sdcard/' + screen_name])
  subprocess.call([ADB_PATH, 'pull', '/sdcard/' + screen_name, screen_path])

  # Return the filename & num so that the screenshot can be accessed
  # programatically.
  return [screen_path, screenshot_num]


def find_view_idx(vc_dump, activity, frag_list):
  """Find the index of the current View in the view array (-1 if new view)."""
  for i in range(len(view_array)):
    if view_array[i].is_duplicate(activity,
                                  frag_list, vc_dump):
      return i
  return -1


def create_view(package_name, vc_dump, activity, frag_list, debug):
  """Store the current view in the View data structure."""
  screenshot_info = save_screenshot(package_name, activity, frag_list)
  v = View(activity, frag_list, vc_dump,screenshot_info[0], screenshot_info[1])

  for component in v.hierarchy:
    # TODO(afergan): For now, only click on certain components, and allow custom
    # components. Evaluate later if this is worth it or if we should just click
    # on everything attributed as clickable.

    # TODO(afergan): Should we include clickable ImageViews? Seems like a lot of
    # false clicks for this so far...
    if component.isClickable():
      print (component['class'] + ' ' + str(component.getX()) + ' '
             + str(component.getY()))
    if (component.isClickable() and component.getVisibility() == VISIBLE and
        component.getX() >= 0 and component.getY() <= MAX_WIDTH and
        component['layout:layout_width'] > 0 and
        component.getY() >= (NAVBAR_HEIGHT) and
        component.getY() <= MAX_HEIGHT and
        component['layout:layout_height'] > 0 and
        ('Button' in component['class'] or
         'TextView' in component['class'] or
         'ActionMenuItemView' in component['class'] or
         'Spinner' in component['class'] or
         (component['class'] ==
          'com.android.settings.dashboard.DashboardTileView')  or
         component['class'] == 'android.widget.ImageView' or
         component.parent == 'android.widget.ListView'
         'android' not in component['class']) and
         # TODO(afergan): Remove this.
         # For debugging purposes, get rid of the phantom clickable components
         # that Zagat creates.
         not (debug and component.getXY() == (0, 273))):
      print component['class'] + '-- will be clicked'
      v.clickable.append(component)

  return v


def crawl_package(apk_dir, package_name, vc, device, debug):
  """Main crawler loop. Evaluate views, store new views, and click on items."""

  if not debug:
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
  global view_root
  view_root = create_view(package_name, vc_dump, activity,
                          frag_list, debug)
  view_array.append(view_root)

  while True:

    if device.isKeyboardShown():
      perform_press_back()

    # Determine if this is a View that has already been seen.
    view_idx = find_view_idx(vc_dump, activity, frag_list)
    if view_idx >= 0:
      print '**FOUND DUPLICATE'
      curr_view = view_array[view_idx]
    else:
      print '**NEW VIEW'
      curr_view = create_view(package_name, vc_dump, activity, frag_list, debug)
      view_array.append(curr_view)

    print 'Num clickable: ' + str(len(curr_view.clickable))

    if curr_view.clickable:
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
      perform_press_back()
      if curr_view == view_root:
        return

    vc_dump = vc.dump(window='-1')
    activity = get_activity_name(package_name)
    if activity == EXITED_APP:
      return
    frag_list = get_frag_list(package_name)

