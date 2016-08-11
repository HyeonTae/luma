# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""Create a image based representation for each UI.

This script uses the data about the UI elements in the view hierarchy to create
a representation of the UI. This representation marks different elements as
text, icons or images.

"""

import argparse
import colorsys
import json
import numpy as np
import os

from PIL import Image, ImageDraw
from scipy import stats

DEVICE_WIDTH = 1440
DEVICE_HEIGHT = 2560
LUMINANCE_THRESHOLD = 2
HUE_THRESHOLD = 1
THUMBNAIL_HEIGHT = 100

IMAGE_MAX_SIZE = 0.75
ICON_MAX_SIZE = 0.15

# The boundaries of elements are shrunk by these many pixels on all sides.
PADDING = 10


def get_elem_bounds(element):
  """Returns bounds for leaf nodes of the view hierarchy."""
  text_bounds = []
  image_bounds = []
  if element.get('children'):
    for child in element['children']:
      t_bounds, i_bounds = get_elem_bounds(child)
      text_bounds += t_bounds
      image_bounds += i_bounds
  elif element.get('visible-to-user'):
    text = element.get('text')
    elem_bounds = element.get('bounds')
    if text:
      text_bounds.append(elem_bounds)
    else:
      image_bounds.append(elem_bounds)
  return (text_bounds, image_bounds)


def are_imgs_natural(orig_image, image_bounds):
  """Determines natural images based on the entropy of hue and luminance."""

  rgb_to_hsv = np.vectorize(colorsys.rgb_to_hsv)
  is_natural = []
  for bound in image_bounds:
    image = orig_image.copy()
    width, height = image.size
    subimage = image.crop(bound)
    s_width, s_height = subimage.size
    arr = np.array(np.asarray(subimage).astype('float'))
    r, g, b = np.rollaxis(arr, axis=-1)
    h = rgb_to_hsv(r, g, b)[0]
    hist_h = np.histogram(h, bins=32, range=(0.0, 1.0))
    hist_h = list(hist_h[0])
    hist_h = [h/float(sum(hist_h)) for h in hist_h]
    entropy_h = stats.entropy(hist_h)

    subimage_l = image.crop(bound).convert('L')
    hist_l = subimage_l.histogram()
    hist_l = [h/float(sum(hist_l)) for h in hist_l]
    entropy_l = stats.entropy(hist_l)

    # Images larger than a certain size are assumed to be natural images.
    if (float(s_width)/width < ICON_MAX_SIZE and
        float(s_height)/height < ICON_MAX_SIZE):
      is_natural.append(entropy_l > LUMINANCE_THRESHOLD or
                        entropy_h > HUE_THRESHOLD)
    else:
      is_natural.append(True)
    image.close()
    subimage.close()
    subimage_l.close()
  return is_natural


if __name__ == '__main__':
  parser = argparse.ArgumentParser()
  parser.add_argument('data_folder_path',
                      help=('Full path to the data folder. It could contain '
                            'multiple folders for different sessions inside it.'
                           ))
  args = parser.parse_args()
  data_folder_path = args.data_folder_path

  out_view = {}
  session_ids = [f for f in os.listdir(data_folder_path) if
                 os.path.isdir(os.path.join(data_folder_path, f))]
  for session_id in session_ids:
    print session_id
    try:
      json_folder = os.path.join(data_folder_path, session_id, 'rico_views')
      view_nums = [f.split('.')[0] for f in os.listdir(json_folder)
                   if '.json' in f]
    except OSError:
      # If there is a problem reading data for a session, we skip that session.
      print 'OSError'

    for view_num in view_nums:
      print view_num
      try:
        with open(os.path.join(json_folder, view_num + '.json')) as data_file:
          view = json.load(data_file)
        img_path = os.path.join('processed_data', session_id, 'img',
                                view_num + '.png')
      except IOError:
        # If there is a problem reading the JSON file or the screenshot for a
        # UI, we can skip it.
        print 'IOError'

      image = Image.open(img_path)
      width, height = image.size

      blank_image = Image.new('RGB', (width, height), 'white')
      draw = ImageDraw.Draw(blank_image)
      x_factor = width/float(DEVICE_WIDTH)
      y_factor = height/float(DEVICE_HEIGHT)

      # Create three new binary images, one for each of text, icon and image
      # elements in the UI.
      ae_img_1 = Image.new('1', (width, height), 'white')
      ae_img_2 = Image.new('1', (width, height), 'white')
      ae_img_3 = Image.new('1', (width, height), 'white')
      draw_ae_1 = ImageDraw.Draw(ae_img_1)
      draw_ae_2 = ImageDraw.Draw(ae_img_2)
      draw_ae_3 = ImageDraw.Draw(ae_img_3)

      # First we categorize elements as text and images.
      t_elem_bounds, i_elem_bounds = get_elem_bounds(view['activity']['root'])
      t_element_bounds = [[int(bound[0] * x_factor), int(bound[1] * y_factor),
                           int(bound[2] * x_factor), int(bound[3] * y_factor)]
                          for bound in t_elem_bounds]
      i_element_bounds = [[int(bound[0] * x_factor), int(bound[1] * y_factor),
                           int(bound[2] * x_factor), int(bound[3] * y_factor)]
                          for bound in i_elem_bounds]

      # We remove elements with zero areas.
      t_element_bounds = [bound for bound in t_element_bounds
                          if bound[0] < bound[2] and bound[1] < bound[3]]
      i_element_bounds = [bound for bound in i_element_bounds
                          if bound[0] < bound[2] and bound[1] < bound[3]]

      # Determine which image elements are natural and which are icons.
      is_natural = are_imgs_natural(image, i_element_bounds)

      for idx, bound in enumerate(i_element_bounds):
        # Images larger than a certain size are discarded as they are most
        # likely a background image that does not contribute to the UI.
        if (float(bound[2] - bound[0])/width > IMAGE_MAX_SIZE and
            float(bound[3] - bound[1])/height > IMAGE_MAX_SIZE):
          continue

        # We shrink the elements before drawing them to make sure the separation
        # between them are preserved even in the thumbnails that we input to the
        # autoencoder.
        inner_bound = [bound[0] + PADDING, bound[1] + PADDING,
                       bound[2] - PADDING, bound[3] - PADDING]
        if inner_bound[0] >= inner_bound[2] or inner_bound[1] >= inner_bound[3]:
          pass

        if is_natural[idx]:
          draw.rectangle(inner_bound, fill=(255, 0, 0, 0))
          draw_ae_3.rectangle(inner_bound, 'black')
        else:
          draw.rectangle(inner_bound, fill=(0, 255, 0, 0))
          draw_ae_2.rectangle(inner_bound, 'black')

      # Draw text after images because many a times there is text over images.
      for idx, bound in enumerate(t_element_bounds):
        inner_bound = [bound[0] + PADDING, bound[1] + PADDING,
                       bound[2] - PADDING, bound[3] - PADDING]
        draw.rectangle(inner_bound, fill=(0, 0, 255, 0))
        draw_ae_1.rectangle(inner_bound, 'black')

      thumbnail_height = THUMBNAIL_HEIGHT
      thumbnail_width = int(width*thumbnail_height/height)
      ae_img_1 = ae_img_1.resize((thumbnail_width, thumbnail_height),
                                 Image.ANTIALIAS)
      ae_img_2 = ae_img_2.resize((thumbnail_width, thumbnail_height),
                                 Image.ANTIALIAS)
      ae_img_3 = ae_img_3.resize((thumbnail_width, thumbnail_height),
                                 Image.ANTIALIAS)

      ae_img = Image.new('1', (3 * thumbnail_width, thumbnail_height), 'white')
      ae_img.paste(ae_img_1, (0, 0))
      ae_img.paste(ae_img_2, (thumbnail_width, 0))
      ae_img.paste(ae_img_3, (2 * thumbnail_width, 0))

      # The ae_imgs folder contains all the images to be used for training the
      # autoencoder.
      if not os.path.exists('ae_imgs'):
        os.makedirs('ae_imgs')
      ae_img.save(os.path.join('ae_imgs', session_id + '_' + view_num + '.png'))

      # We save a color coded representation of the UI back in each session
      # in the data folder
      ui_folder = os.path.join('processed_data', session_id, 'ui_imgs')
      if not os.path.exists(ui_folder):
        os.makedirs(ui_folder)
      blank_image.save(os.path.join(ui_folder, view_num + '.png'))
      ae_img.save(os.path.join(ui_folder, view_num + '_ae.png'))

      image.close()
      blank_image.close()
      ae_img_1.close()
      ae_img_2.close()
      ae_img_3.close()
      ae_img.close()

