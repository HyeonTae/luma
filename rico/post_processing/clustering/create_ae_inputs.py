# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""Create a numpy array that can be used as input to the autoencoder.

This script takes in all the input images and combines them into a two
dimensional numpy array that can be used as an input to an autoencoder.

"""

import json
import os
import numpy
import scipy
import sys

from PIL import Image


if __name__ == '__main__':
  img_names = [f for f in os.listdir('ae_imgs') if '.png' in f]
  images = []
  image_names = []
  for idx, img_name in enumerate(img_names):
    if idx % 100 == 0:
      print str(idx) + '/' + str(len(img_names))
    img_path = os.path.join('ae_imgs', img_name)
    image = Image.open(img_path)
    np_img = numpy.array(image.convert('L'))

    # If there are malformed input images, we ignore them.
    if np_img.shape[0]*np_img.shape[1] == 16800:
      images.append(list(numpy.ravel(np_img)))
      image_names.append(img_name)
      image.close()

  numpy.save('ae_inputs.npy', numpy.array(images))
  # We save the name of the image that each row of ae_inputs corresponds to.
  # This helps visualize results later.
  with open('image_names.json', 'w') as outfile:
    json.dump({'img_names': image_names}, outfile)
