# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""Convert data to format used by RICO.

This script converts the XML view hierarchy data to the JSON format used by
RICO.

"""

import argparse
import json
import os
import re
import shutil
import xml.etree.ElementTree as ET

TRUTHY_VALUES = ['true']


def make_json_node(xml_node):
  """Converts a node in the view hierarchy to JSON."""
  def to_bool(string):
    return string in TRUTHY_VALUES

  node = {}
  node['class'] = xml_node.attrib.get('class')
  node['visibility'] = xml_node.attrib.get('visibility')
  node['visible-to-user'] = to_bool(xml_node.attrib.get('visible-to-user'))
  node['adapter-view'] = to_bool(xml_node.attrib.get('adapter-view'))
  node['focusable'] = to_bool(xml_node.attrib.get('focusable'))
  node['enabled'] = to_bool(xml_node.attrib.get('enabled'))
  node['draw'] = to_bool(xml_node.attrib.get('draw'))
  node['scrollable-horizontal'] = to_bool(xml_node.attrib.get(
      'scrollable-horizontal'))
  node['scrollable-vertical'] = to_bool(xml_node.attrib.get(
      'scrollable-vertical'))
  node['clickable'] = to_bool(xml_node.attrib.get('clickable'))
  node['pointer'] = xml_node.attrib.get('pointer')
  node['long-clickable'] = to_bool(xml_node.attrib.get('long-clickable'))
  node['focused'] = to_bool(xml_node.attrib.get('focused'))
  node['selected'] = to_bool(xml_node.attrib.get('selected'))
  node['pressed'] = to_bool(xml_node.attrib.get('pressed'))
  node['abs-pos'] = to_bool(xml_node.attrib.get('abs-pos'))
  node['text'] = xml_node.attrib.get('text')
  bounds = xml_node.attrib.get('bounds')
  if bounds:
    p = re.compile('\[(-?\d*),(-?\d*)\]\[(-?\d*),(-?\d*)\]')
    m = p.match(bounds)
    node['bounds'] = [int(m.group(1)), int(m.group(2)), int(m.group(3)),
                      int(m.group(4))]
  else:
    node['bounds'] = None
  node['resource-id'] = xml_node.attrib.get('resource-id')
  node['package'] = xml_node.attrib.get('package')
  node['content-desc'] = xml_node.attrib.get('content-desc')
  children = []
  for child in xml_node:
    children.append(make_json_node(child))
  node['children'] = children
  return node

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('data_folder_path',
                      help=('Full path to the data folder. It could contain '
                            'multiple folders for different sessions inside it.'
                           ))
  args = parser.parse_args()
  data_folder_path = args.data_folder_path

  out_view = {}
  session_ids = [f for f in os.listdir(data_folder_path) if os.path.isdir(
      os.path.join(data_folder_path, f))]
  for session_id in session_ids:
    try:
      view_nums = [f.split('.')[0] for f in os.listdir(
          os.path.join(data_folder_path, session_id, 'xml'))
                   if '.xml' in f]
    except OSError:
      shutil.rmtree(os.path.join('processed_data', session_id))
    print session_id
    for view_num in view_nums:
      print view_num

      # If the input XML or JSON file cannot be parsed we skip that view.
      try:
        tree = ET.parse(os.path.join('processed_data', session_id, 'xml',
                                     view_num + '.xml'))
      except ET.ParseError:
        print 'Error parsing XML file.'
        continue
      xml_root = tree.getroot()

      try:
        with open(os.path.join('processed_data', session_id, 'xml',
                               view_num + '.json')) as data_file:
          data = json.load(data_file)
      except IOError:
        print 'Error loading JSON file.'
        continue

      out_view['activity_name'] = data['DDDG_Current_Activity']
      activity = {'root': make_json_node(xml_root)}
      activity['added_fragments'] = data['DDDG_Added_Fragments']
      activity['active_fragments'] = data['DDDG_Active_Fragments']
      activity['is_keyboard_deployed'] = data['DDDG_Keyboard_Deployed']
      out_view['activity'] = activity

      outfolder = os.path.join('processed_data', session_id, 'rico_views')
      if not os.path.exists(outfolder):
        os.makedirs(outfolder)

      outfile_name = os.path.join(outfolder, view_num + '.json')

      with open(outfile_name, 'w') as outfile:
        json.dump(out_view, outfile, indent=2)
