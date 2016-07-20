# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""A script to aid debugging the view hierarchy data.

This script helps visualize the view hierarchy by drawing the bounds
of all clickable elements on a screenshot of the UI.

Use this script with an Android device (or emulator) connected to your
machine.

"""

import json
import os
import platform
import socket
import subprocess

from PIL import Image, ImageDraw
from subprocess import call

ADB = None
# The following dimensions are for a Nexus 6P device.
DEVICE_WIDTH = 1440
DEVICE_HEIGHT = 2560

def set_adb_path():
  """Define the ADB path based on operating system."""
  try:
    global ADB
    # For machines with multiple installations of adb, use the last listed
    # version of adb.
    ADB = subprocess.check_output(['which -a adb'], shell=True).split('\n')[-2]
  except subprocess.CalledProcessError:
    print 'Could not find adb. Please check your PATH.'

def _clickable_elements_bounds(element):
  bounds = []
  if element.get("children"):
    for child in element["children"]:
      bounds += _clickable_elements_bounds(child)
  if element["clickable"] and element["visibility"] == "visible":
    bounds.append(element["bounds"])
  return bounds


def clickable_elements_bounds(view):
  root = view["activity"]["root"]
  return _clickable_elements_bounds(root)

if __name__ == "__main__":
  set_adb_path()
  # If multiple phones are connected you would need to specify which phone
  # an ADB command is directed at using the -s flag.
  call([ADB, "shell", "screencap", "-p", "/sdcard/screen.png"])
  call([ADB, "pull", "/sdcard/screen.png"])
  call([ADB, "forward", "tcp:1699", "tcp:1699"])
  call([ADB, "shell", "dumpsys", "activity", "start-view-server"])

  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server_address = ("localhost", 1699)

  try:
    sock.connect(server_address)
    message = "d\n"  # This is command to dump the view hierarchy.
    sock.sendall(message)
    response = ""
    while True:
      data = sock.recv(16)
      response += str(data)
      # A valid response ends with "RICO_JSON_END".
      if "RICO_JSON_END" in response:
        break
  finally:
    sock.close()

  view = json.loads(response.split("RICO_JSON_END")[0])

  image = Image.open("screen.png")
  width, height = image.size
  # Resize the image to make it easier to view.
  image.thumbnail((width/4, height/4), Image.ANTIALIAS)
  width, height = image.size

  draw = ImageDraw.Draw(image)
  x_factor = width/float(DEVICE_WIDTH)
  y_factor = height/float(DEVICE_HEIGHT)

  bounds = clickable_elements_bounds(view)
  for bound in bounds:
    new_bound = [int(bound[0] * x_factor), int(bound[1] * y_factor),
                 int(bound[2] * x_factor), int(bound[3] * y_factor)]
    draw.rectangle(new_bound, outline=(0, 0, 255, 0))

  image.save(os.path.join("snapshot.jpg"))
  # Open the saved image using appropriate program based on user's OS.
  if platform.system() == "Linux":
    call(["gnome-open", "snapshot.jpg"])
  elif platform.system() == "Darwin":
    call(["open", "snapshot.jpg"])
