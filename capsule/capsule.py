# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""The main module for the APK Crawler application."""

import getopt
import os
import subprocess
import sys
import time

from com.dtmilano.android.common import obtainAdbPath
from com.dtmilano.android.viewclient import ViewClient
import crawlpkg

ADB_PATH = obtainAdbPath()
HELP_MSG = ('Capsule usage:\n'
            'python capsule.py DEVICE_SERIAL [flag] <argument>\n'
            'No command line flags -- crawl current package\n'
            '-d or --dir /PATH_TO_APKS/  -- install and run APKS from a '
            'directory.\n'
            '-f or --file /[PATH TO FILE]/list.txt -- load text file of '
            'package names on device and crawl them.\n'
            '-r or --recrawl -- recrawl already explored apps.\n'
            '-h or --help -- help, list options')

# PyDev sets PYTHONPATH, use it
try:
  for p in os.environ['PYTHONPATH'].split(':'):
    if p not in sys.path:
      sys.path.append(p)
except KeyError:
  print 'Please set the environment variable PYTHONPATH'

try:
  sys.path.append(os.path.join(os.environ['ANDROID_VIEW_CLIENT_HOME'], 'src'))
except KeyError:
  print 'Please set the environment variable ANDROID_VIEW_CLIENT_HOME'


def load_pkgs_from_dir(dir_path):
  """Return all of the package names in a directory."""

  # Allow user to input either relative or absolute path to directory.
  directory = os.path.join(os.getcwd() + dir_path)
  if os.path.exists(directory):
    names = sorted(os.listdir(directory))
    pkg_list = [os.path.join(directory + n) for n in names if '.apk' in n]
  elif os.path.exists(dir_path):
    names = sorted(os.listdir(dir_path))
    pkg_list = [os.path.join(dir_path + n) for n in names if '.apk' in n]
  else:
    print 'Directory does not exist.'
    return []

  return pkg_list


def load_pkgs_from_file(filename):
  """Return all of the package names listed in a text file."""

  # Allow user to input either relative or absolute path.
  f = os.path.join(os.getcwd() + filename)
  if os.path.isfile(f):
    pkg_list = [pkg.strip('\n') for pkg in open(f)]
    return sorted(pkg_list)
  elif os.path.isfile(filename):
    pkg_list = [pkg.strip('\n') for pkg in open(filename)]
    return sorted(pkg_list)
  else:
    print 'File does not exist.'
    return []


if __name__ == '__main__':

  # Should we uninstall APKs once we install them. Setting it to true allows us
  # to do bulk crawling since we do not need to worry about the device memory
  # filling up.
  uninstall = False
  recrawl = False
  package_list = []

  try:
    kwargs1 = {'verbose': True, 'ignoresecuredevice': True, 'timeout': 20}
    kwargs2 = {'startviewserver': True, 'forceviewserveruse': True,
               'autodump': False, 'ignoreuiautomatorkilled': True}
    device, serialno = ViewClient.connectToDeviceOrExit(**kwargs1)
    vc = ViewClient(device, serialno, **kwargs2)
  except (RuntimeError, subprocess.CalledProcessError):
    print 'Error, device not found or not specified.'
    print HELP_MSG
    sys.exit()

  if any(a in sys.argv for a in ['-h', '--help']):
    print HELP_MSG
    sys.exit()

  # User only specified emulator name or nothing at all.
  if len(sys.argv) <= 2:
    print 'No command line arguments, crawling currently launched app.'
    crawlpkg.crawl_package(vc, device, serialno)
  # Command line argument is only valid if the user entered the filename,
  # emulator name, one option flag, and one argument.
  elif len(sys.argv) == 3:
    print 'Invalid argument structure.'
    print HELP_MSG
  elif len(sys.argv) >= 4:
    try:
      opts, _ = getopt.getopt(sys.argv[2:], 'd:f:h:r', ['directory=', 'file='])
    except getopt.GetoptError as err:
      print str(err)
      print HELP_MSG
      sys.exit()

    # This infrastructure allows us to add additional command line argument
    # possibilities easily.
    for opt, arg in opts:
      if opt in ('-d', '--dir'):
        uninstall = True
        package_list = load_pkgs_from_dir(arg)
      elif opt in ('-f', '--file'):
        package_list = load_pkgs_from_file(arg)
      elif opt in ('-h', '--help'):
        print HELP_MSG
      elif opt in ('-r', '--recrawl'):
        recrawl = True
      else:
        print ('Unhandled option. Use -h or --help for a listing of '
               'commands')
        sys.exit()

    if package_list:
      print 'Packages to be crawled: ' + ', '.join(package_list)

    for package in package_list:
      # Possibly install, then launch and crawl the app. device.shell() does
      # not support the install or launch.
      package_name = ''
      should_crawl = True
      if '.apk' in package:
        package_name = crawlpkg.extract_between(package, '/', '.apk', -1)
        subprocess.call([ADB_PATH, '-s', serialno, 'install', '-r', package])

      else:
        # We have the package name but not the .apk file.
        package_name = package.split('/')[-1]
        # Make sure the package is installed on the device by checking it
        # against installed third-party packages.
        installed_pkgs = subprocess.check_output([ADB_PATH, '-s', serialno,
                                                  'shell', 'pm',
                                                  'list packages', '-3'])
        if package_name not in installed_pkgs:
          print 'Cannot find the package on the device.' + package_name
          should_crawl = False

      if os.path.exists(os.path.dirname(os.path.abspath(__file__)) + '/data/' +
                        package_name) and not recrawl:
        should_crawl = False

      if should_crawl:
        print 'Crawling ' + package_name

        # Launch the app.
        subprocess.call([ADB_PATH, '-s', serialno, 'shell', 'monkey', '-p',
                         package_name, '-c', 'android.intent.category.LAUNCHER',
                         '1'])
        time.sleep(5)

        crawlpkg.crawl_package(vc, device, serialno, package_name)

        if uninstall:
          print 'uninstall' + package_name
          subprocess.call([ADB_PATH, '-s', serialno, 'uninstall', package_name])

  else:
    print 'Invalid number of command line arguments.'
    print HELP_MSG
