# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""Creates HTML files to visualize the images in different clusters."""

import argparse
import json
import numpy as np
import os

from random import randint


def write_html(img_names, k, label, data_folder_path):
  """Creates a HTML file for each cluster."""

  folder_name = os.path.join('cluster_viz', str(k))
  if not os.path.exists(folder_name):
    os.makedirs(folder_name)

  html_filename = os.path.join(folder_name, str(label) + '.html')
  # If the file exists, delete it.
  if os.path.exists(html_filename):
    os.remove(html_filename)

  # Many screens form the a session would be the same. We want to show only
  # one of those screens. So we use the list of unique views from each session.
  with open('unique_views.json') as namefile:
    unique_views = json.loads(namefile.read())

  with open(html_filename, 'a') as html_file:
    html_file.write('<!DOCTYPE html>\n')
    html_file.write('<html>\n')
    html_file.write('  <head>\n')
    html_file.write('    <title>Clusters</title>\n')
    html_file.write('  </head>\n')
    html_file.write('  <body>\n')

    html_file.write('    <div>')
    # We provide links at the top of the HTML file to go to the previous, next,
    # or a random cluster. This helps when visually inspecting clusters.
    if label != 1:
      html_file.write(('      <a style="padding-right:30px" href="./{}.html">'
                       'Previous</a>').format(str(label - 1)))
    html_file.write(('      <a style="padding-right:30px" href="./{}.html">'
                     'Random</a>').format(str(randint(1, k))))
    if label != k:
      html_file.write('      <a align="right" href="./{}.html">Next</a>'.format(
          str(label + 1)))
    html_file.write('    </div>')

    for img_name in img_names:
      session_id, img = img_name.split('_')
      views = unique_views.get(str(session_id), [])
      if views and img.split('.')[0] in views:
        html_file.write('    <div style="vertical-align: top; display:'
                        ' inline-block; text-align: center;">')
        html_file.write(('      <img alt={} src="{}/{}/img/{}" style="height: '
                         '300px; padding: 0px;">\n').format(
                             str(img_name), data_folder_path, session_id, img))
        html_file.write('    </div>')
    html_file.write('  </body>\n')
    html_file.write('</html>\n')

if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('data_folder_path',
                      help=('Full path to the data folder. It could contain '
                            'multiple folders for different sessions inside it.'
                           )
                     )
  args = parser.parse_args()
  data_folder_path = args.data_folder_path

  ks = [2**exp for exp in range(5, 11)]
  with open('image_names.json') as namefile:
    image_names = json.loads(namefile.read())['img_names']

  print len(image_names)

  for k in ks:
    print 'K:    ' + str(k)
    labels = np.load('clusters/labels_' + str(k) + '.npy')
    for label in range(1, k + 1):
      indices = [i for i, j in enumerate(labels) if j == label]
      img_names = [image_names[idx] for idx in indices]
      write_html(img_names, k, label, data_folder_path)

