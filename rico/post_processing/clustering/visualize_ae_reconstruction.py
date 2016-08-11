# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""Shows the reconstructed images for a random sample of images."""

import numpy as np
import os

from PIL import Image
from random import randint


if __name__ == '__main__':
  orig_imgs = np.load('ae_inputs.npy').astype(float)
  reconstructed_imgs = np.load('decoded_imgs.npy').astype(float)*255.0

  assert orig_imgs.shape[0] == reconstructed_imgs.shape[0]
  if not os.path.exists('reconstructed_imgs'):
    os.makedirs('reconstructed_imgs')

  n = 30  # Number of images we want to reconstruct.
  for j in range(n):
    # Pick a random image to reconstruct.
    i = randint(0, orig_imgs.shape[0] - 1)
    img_name = 'ae_test_' + str(j) + '_' + str(i) + '.png'
    img_path = os.path.join('reconstructed_imgs', img_name)

    img1 = Image.fromarray(orig_imgs[i].reshape(100, 168)).convert('L')
    img2 = Image.fromarray(reconstructed_imgs[i].reshape(100, 168)).convert('L')
    width, height = img1.size
    image = Image.new('L', (2 * width, height), 'white')
    image.paste(img1, (0, 0))
    image.paste(img2, (width, 0))

    image.save(img_path)
    image.close()
