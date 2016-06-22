#!/usr/bin/python2.7
# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""Continuously capture screenshots from an Android emulator instance.

Launches Xvfb with supplied display number, launches android emulator with
supplied avd name on that display, and captures the Xvfb framebuffer in a loop
as JPEG images and outputs in through a TCP socket in a format similar to
Minicap (https://github.com/openstf/minicap).
"""
import argparse
import atexit
import os
import re
import socket
import struct
from subprocess import PIPE
from subprocess import Popen
import time
import traceback

# The depth needed for the emulator is minimum of 24
# The size should be changed if you change the display associated with
# the AVD that you're using with the emulator.
SCREEN_SIZE = "1000x900x24"
# The number of seconds we wait for XVFB to start.
XVFB_WAIT_TIME = 5
# The number of seconds we wait for the emulator to start.
# If we don't wait long enough, we might grab wrong dimension
# for the emulator window (initially it is smaller when it is loading).
EMULATOR_WAIT_TIME = 300
# Each display is assigned a port number that starts from this port
# Display :0 will be port 6100, display :1 will be 6101 etc.
BASE_PORT_NUM = 6100
# To be compatible with Minicap, we use a similar header format as specified at
# https://github.com/openstf/minicap (under "Usage")
HEADER_SIZE = 24
HEADER_VERSION = 1

procs = []


@atexit.register
def kill_subprocesses():
  """Auto kill subprocesses (Xvfb and emulator) when this script is killed.

  Details at: http://sharats.me/the-ever-useful-and-neat-subprocess-module.html
  """
  for process in procs:
    process.kill()


def run_shell_cmd(command):
  """Runs the command in a shell and returns a tuple with output and error."""
  try:
    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
  except OSError:
    print "could not run command: " + command
    traceback.print_exc()
  return process.communicate()


def get_window_names(phrase, display_number):
  """Names of all windows on given display whose names contain the phrase."""

  out = run_shell_cmd("xwininfo -display localhost:" + str(display_number) +
                      " -tree -root | grep " + phrase)[0]
  window_names = []
  for line in out.split("\n"):
    try:
      window_names.append(line.split("\"")[1])
    except IndexError:
      print "Window name without a \" was found."
  return window_names


def get_window_details(win_name, display_number):
  """Return the x/y coordinates as well as width/height of a window."""

  out = run_shell_cmd("xwininfo -display localhost:" + str(display_number) +
                      " -name " + win_name)[0]
  lines = out.split("\n")
  x = y = w = h = 0
  xt = yt = wt = ht = False
  for line in lines:
    if "Absolute upper-left X:" in line:
      x = int(re.sub("[^0-9]", "", line))
      xt = True
    elif "Absolute upper-left Y:" in line:
      y = int(re.sub("[^0-9]", "", line))
      yt = True
    elif "Width:" in line:
      w = int(re.sub("[^0-9]", "", line))
      wt = True
    elif "Height:" in line:
      h = int(re.sub("[^0-9]", "", line))
      ht = True
  if xt and yt and wt and ht:
    return (x, y, w, h)
  else:
    raise RuntimeError("Could not find position or size of specified window.")


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("display_num", help="The display number to use with Xvfb",
                      type=int)
  parser.add_argument("avd_name", help="The name of the AVD instance to use")
  args = parser.parse_args()
  display_num = args.display_num
  avd_name = args.avd_name

  # Folder where xvfb will store its framebuffer as a memory mapped file.
  # We create a separate subdirectory under /var/tmp for each display.
  fbdir = os.path.join("/var/tmp", str(display_num))
  if not os.path.exists(fbdir):
    os.mkdir(fbdir)

  # Start xvfb and give it a few seconds to start.
  cmd = ["Xvfb", ":"+str(display_num), "-ac", "-fbdir", fbdir, "-screen", "0",
         SCREEN_SIZE]
  proc_xvfb = Popen(cmd, stdout=PIPE, stderr=PIPE)
  procs.append(proc_xvfb)
  time.sleep(XVFB_WAIT_TIME)
  print "display: " + str(display_num)

  # Run the emulator on the display created by Xvfb.
  cmd = ("DISPLAY=:" + str(display_num) + " emulator64-x86 -avd " + avd_name +
         " -noaudio -nojni -netfast -no-boot-anim -qemu -enable-kvm -snapshot")
  proc_emulator = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
  procs.append(proc_emulator)
  time.sleep(EMULATOR_WAIT_TIME)

  # We assume that each display will only have one window with an emulator.
  # We locate it by using the fact that the window name contains the avd_name
  # that we specify when running the emulator.
  window_name = get_window_names(avd_name, display_num)[0]
  window_x, window_y, window_width, window_height = get_window_details(
      window_name, display_num)

  # This is where we start the server that dumps the screenshots as JPEG images
  # The port number assigned is dependent on the diplay number
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  port = BASE_PORT_NUM + display_num
  server_address = ("localhost", port)
  sock.bind(server_address)
  sock.listen(1)

  # This command grabs the pixels corresponding to the emulator window from the
  # Xvfb framebuffer (that is mapped to a file) and converts it to a JPEG image
  # The - argument at the end means that the JPEG image is output to stdout
  cmd = ("convert /var/tmp/" + str(display_num) +
         "/Xvfb_screen0 -crop {}x{}+{}+{} -").format(window_width,
                                                     window_height, window_x,
                                                     window_y)

  # We use a similar header format as Minicap -- specified here
  # https://github.com/openstf/minicap (under "Usage").
  # The only difference is that instead of the real PID we have a number that
  # helps identify the emulator this server is associated with.
  # We grab that number (say "5554") from the window name (which in this case
  # will be 5554:avd_name). We also have the same virtual display width/height
  # as the real display width/height.
  pid = int(window_name.split(":")[0])
  print "emulator: " + str(pid)
  print "port: " + str(port)
  # The struct python library is used to pack different data as bytes.
  # More info here: https://docs.python.org/3/library/struct.html
  global_header = (struct.pack("B", HEADER_VERSION) +
                   struct.pack("B", HEADER_SIZE) +
                   struct.pack("<I", pid) +
                   struct.pack("<I", window_width) +
                   struct.pack("<I", window_height) +
                   struct.pack("<I", window_width) +
                   struct.pack("<I", window_height) +
                   struct.pack("B", 0) +
                   struct.pack("B", 1))

  while True:
    connection, client_address = sock.accept()
    # Every time a new client connects, we send the global header first.
    connection.sendall(global_header)

    try:
      while True:
        proc = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        jpeg, err = proc.communicate()
        # Each frame consist of the frame size as a 4 byte uint32 followed by
        # the actual JPEG bytes.
        frame_size = struct.pack("<I", len(jpeg) + 4)
        frame = frame_size + jpeg
        connection.sendall(frame)
    except socket.error, e:
      # This handles the case when the client disconnects unexpectedly.
      # We just go back to accepting another connection.
      print e
    finally:
      connection.close()


