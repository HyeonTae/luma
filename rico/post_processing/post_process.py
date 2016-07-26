# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""A script to postprocess data collected by Rico.

This script combines data from three sources: images, user event details
(contains view hierarchy details) and logcat output to produce two
visualizations of the user trace.

"""

import argparse
import json
import os

from PIL import Image, ImageDraw

LARGEST_CIRCLE_SIZE = 15
CIRCLE_SIZE_DECREMENT = 0.7
SMALLEST_CIRCLE_SIZE = 5
CIRCLE_COLOR = (0, 0, 255, 0)
CLICKABLE_ELEMENT_COLOR = (0, 0, 255, 0)
CLICKED_ELEMENT_COLOR = (255, 0, 0, 0)
DEVICE_WIDTH = 1440
DEVICE_HEIGHT = 2560
BB_SEPARATION = 1


def makedir(path):
  if not os.path.exists(path):
    os.makedirs(path)


def read_events(folder):
  with open(os.path.join(folder, "events.json")) as json_file:
    events = json.load(json_file)
  return events


def read_logcat(folder):
  with open(os.path.join(folder, "logcats.json")) as json_file:
    logcat = json.load(json_file)
  return logcat


def save_json(jsondata, filename):
  with open(filename, "w") as json_file:
    json.dump(jsondata, json_file, indent=2)


def save_view(folder, img_num, view_hierarchy):
  view_file = os.path.join(folder, "views", str(img_num) + ".json")
  save_json(view_hierarchy, view_file)


def load_view(folder, img_num):
  with open(os.path.join(folder, "views", str(img_num) + ".json")) as json_file:
    view = json.load(json_file)
  return view


def _clickable_elements_bounds(element):
  bounds = []
  if element.get("children"):
    for child in element["children"]:
      bounds += _clickable_elements_bounds(child)
  if element["clickable"] and element["visibility"] == "visible":
    bounds.append(element["bounds"])
  return bounds


def clickable_elements_bounds(view):
  try:
    root = view["activity"]["root"]
    return _clickable_elements_bounds(root)
  except KeyError:
    return []


def _get_bounds_by_pointer(element, pointer):
  if element["pointer"] == pointer:
    return element["bounds"]
  if element.get("children"):
    for child in element["children"]:
      found = _get_bounds_by_pointer(child, pointer)
      if found:
        return found
  return None


def get_bounds_by_pointer(view, pointer):
  root = view["activity"]["root"]
  return  _get_bounds_by_pointer(root, pointer)


def write_html(viz_names, views):
  html_filename = os.path.join(session_path, "viz", "viz.html")
  # If the file exists, delete it.
  if os.path.exists(html_filename):
    os.remove(html_filename)

  with open(html_filename, "a") as html_file:
    html_file.write("<!DOCTYPE html>\n")
    html_file.write("<html>\n")
    html_file.write("  <head>\n")
    html_file.write("    <title>Linear Flow Visualization</title>\n")
    html_file.write("  </head>\n")
    html_file.write("  <body>\n")

    for viz_name in viz_names:
      html_file.write("    <div id=\"header\" style=\"overflow-x: auto;"
                      " white-space: nowrap;\">\n")
      html_file.write("      <div style=\"vertical-align: top; display:"
                      " inline-block; text-align: center;\">\n")
      for view_num in views:
        html_file.write("        <div style=\"vertical-align: top; display:"
                        " inline-block; text-align: center;\">")
        html_file.write("          <img alt=" + str(view_num) + " src=\"./img/"
                        + viz_name + "/" + str(view_num)
                        + ".jpg\" style=\"height: 400px; padding: 30px;\">\n")
        html_file.write("          <span style=\"display: block;"
                        " padding-bottom: 10px;\">" + str(view_num)
                        + "</span>\n")
        html_file.write("        </div>")
      html_file.write("      </div>\n")
      html_file.write("    </div>\n")
    html_file.write("  </body>\n")
    html_file.write("</html>\n")


def sort_events(events):
  """Sorts events based on timestamp."""

  # When multiple events have the same timestamp, we only care about getting the
  # GestureStart and GestureStop events in the right place. Even if the order
  # of the other events in between are off, it does not affect us.
  # We push GestureStarts forwards and GestureStops backwards for breaking ties.

  events = sorted(events, key=lambda k: k["timestamp"])
  for idx in range(len(events) - 1, 0, -1):
    event = events[idx]
    prev_event = events[idx - 1]
    if (prev_event["timestamp"] == event["timestamp"] and
        event["eventName"] == "input.gestureStart" and
        prev_event["eventName"] != "input.gestureStop"):
      events[idx - 1] = event
      events[idx] = prev_event

  for idx in range(1, len(events)):
    event = events[idx]
    prev_event = events[idx - 1]
    if (event["timestamp"] == prev_event["timestamp"] and
        prev_event["eventName"] == "input.gestureStop" and
        event["eventName"] != "input.gestureStart"):
      events[idx - 1] = event
      events[idx] = prev_event

  return events


def get_image_map(img_dir):
  img_names = [name for name in os.listdir(img_dir) if ".jpg" in name]
  img_map = {}
  for img_name in img_names:
    img_num = img_name.split("_")[1]
    img_map[img_num] = img_name
  return img_map


def save_processed_data(folder, views, gesture_coords, click_map):
  processed_data = {"views": views,
                    "gesture_coords": gesture_coords,
                    "click_map": click_map
                   }
  save_json(processed_data, os.path.join(folder, "processed_data.json"))

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("data_folder_path",
                      help=("Full path to the data folder. It could contain "
                            "multiple folders for different sessions inside it."
                           )
                     )
  args = parser.parse_args()
  data_folder_path = args.data_folder_path
  dirs = os.listdir(data_folder_path)
  for session in dirs:
    session_path = os.path.join(data_folder_path, session)
    if os.path.isdir(session_path):
      print session
      events = sort_events(read_events(session_path))

      # These hold overall data for all the views.
      views = []
      gesture_coords = {}

      # We go over all the events and group them into different gestures (events
      # from one GestureStart to the corresponding GestureStop).
      gesture_started = False
      gesture_type = "click"
      gesture_view_num = ""
      view_hierarchy = None
      coords = []
      makedir(os.path.join(session_path, "views"))
      for event in events:
        img_num = event["imgId"].split("_")[1]
        if gesture_started and event["x"]:
          coords.append((event["x"], event["y"]))
        if event["eventName"] == "input.gestureStart":
          gesture_started = True
          gesture_view_num = str(img_num)
          try:
            view_hierarchy = json.loads(
                event["viewHierarchy"].split("RICO_JSON_END")[0])
          except ValueError, e:
            # This exception happens when Rico did not capture any JSON for this
            # view. We ignore this case and move on.
            print "JSON Missing: " + event["imgId"]
          save_view(session_path, img_num, view_hierarchy)
          views.append(str(img_num))
        if event["eventName"] == "input.gestureStop":
          gesture_started = False
          gesture_coords[gesture_view_num] = coords
          coords = []

      # Process logcat to identify elements that were clicked.
      click_map = {}  # Maps view_id to the pointer name of clicked element.
      logcat = read_logcat(session_path)
      logcat = sorted(logcat, key=lambda k: k["timestamp"])
      view_id = None
      for log_item in logcat:
        message = log_item["logcatMessage"]
        if "Request_ID" in message:
          view_id = message.split(":")[-2]
        if ":click:" in message:
          pointer = message.split(":")[2]
          click_map[str(view_id).strip()] = str(pointer).strip()

      # Generate a map from img numbers to names.
      img_map = get_image_map(os.path.join(session_path, "img"))

      # For each image corresponding to a view, produce two processed images.
      gesture_imgs_path = os.path.join(session_path, "viz", "img", "gestures")
      elements_imgs_path = os.path.join(session_path, "viz", "img", "elements")
      makedir(gesture_imgs_path)
      makedir(elements_imgs_path)

      # Produce image showing gesture.
      for idx, view_num in enumerate(views):
        image = Image.open(os.path.join(session_path, "img", img_map[view_num]))
        draw = ImageDraw.Draw(image)
        r = LARGEST_CIRCLE_SIZE
        width, height = image.size
        # We draw a circle for each (x, y) co-ordinate pair in a gesture.
        coords = gesture_coords[str(view_num)]
        for coord in coords:
          x = coord[0] * width
          y = coord[1] * height
          ellipse_coordinates = (x - r, y - r, x + r, y + r)
          draw.ellipse(ellipse_coordinates, fill=CIRCLE_COLOR)
          if r > SMALLEST_CIRCLE_SIZE:
            r -= CIRCLE_SIZE_DECREMENT
        image.save(os.path.join(gesture_imgs_path, view_num + ".jpg"))

      # Produce image showing clickable elements.
      for idx, view_num in enumerate(views):
        image = Image.open(os.path.join(session_path, "img", img_map[view_num]))
        draw = ImageDraw.Draw(image)
        width, height = image.size

        try:
          view = load_view(session_path, view_num)
          bounds = clickable_elements_bounds(view)
          if width < height:
            # Portrait mode.
            x_factor = width/float(DEVICE_WIDTH)
            y_factor = height/float(DEVICE_HEIGHT)
          else:
            # Landscape mode.
            x_factor = width/float(DEVICE_HEIGHT)
            y_factor = height/float(DEVICE_WIDTH)
          for bound in bounds:
            new_bound = [int(bound[0] * x_factor), int(bound[1] * y_factor),
                         int(bound[2] * x_factor), int(bound[3] * y_factor)]
            draw.rectangle(new_bound, outline=CLICKABLE_ELEMENT_COLOR)

          # The element that was clicked (as detected from logcat) will be
          # highlighted in a different color.
          if view_num in click_map:
            pointer = click_map[view_num]
            bound = get_bounds_by_pointer(view, pointer)
            bound = [int(bound[0] * x_factor), int(bound[1] * y_factor),
                     int(bound[2] * x_factor), int(bound[3] * y_factor)]
            # We draw multiple boxes, one within the other (drawn DIFF pixels
            # apart) to highlight this element.
            for i in range(20):
              bound = [bound[0] + BB_SEPARATION, bound[1] + BB_SEPARATION,
                       bound[2] - BB_SEPARATION, bound[3] - BB_SEPARATION]
              color = CLICKED_ELEMENT_COLOR
              draw.rectangle(bound, outline=color)
        except (IOError, KeyError):
          # This exception happens when Rico did not capture any JSON for this
          # view. We ignore this case and move on.
          pass

        image.save(os.path.join(elements_imgs_path, view_num + ".jpg"))

      viz_names = ["gestures", "elements"]
      write_html(viz_names, views)

      save_processed_data(session_path, views, gesture_coords, click_map)
