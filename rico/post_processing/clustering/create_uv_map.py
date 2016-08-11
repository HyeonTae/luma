# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""Stores the unique views for each session in a dictionary."""

import json
import os


if __name__ == '__main__':
  session_ids = [f for f in os.listdir('processed_data') if
                 os.path.isdir(os.path.join('processed_data', f))]
  uv_views = {}
  for session_id in session_ids:
    views = []
    with open(os.path.join('processed_data', session_id,
                           'view_data.json')) as data_file:
      uvs = json.load(data_file)['uvs']
      for key in uvs:
        views.append(str(uvs[key][0]))
    if views:
      uv_views[str(session_id)] = views
    print session_id + ': ' + str(len(views))

  with open('unique_views.json', 'w') as outfile:
    json.dump(uv_views, outfile, indent=2)
