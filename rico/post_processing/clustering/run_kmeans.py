# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""Runs the k-means clustering algorithms on the encoded images."""

import matplotlib.pyplot as plt
import numpy as np
import os

from keras.models import model_from_json
from sklearn.cluster import KMeans
from theano import theano


def encode_images(images):
  """Encodes images using model saved to disk earlier."""

  json_file = open('model.json', 'r')
  loaded_model_json = json_file.read()
  json_file.close()
  model = model_from_json(loaded_model_json)
  model.load_weights('model.h5')
  model.compile(optimizer='adadelta', loss='binary_crossentropy')
  get_activations = theano.function([model.layers[0].input],
                                    model.layers[3].output,
                                    allow_input_downcast=True)
  data = get_activations(images)
  np.save('encoded_imgs.npy', data)

if __name__ == '__main__':
  data = np.load('encoded_imgs.npy')
  print data.shape

  k_values = [2**exp for exp in range(5, 11)]

  if not os.path.exists('clusters'):
    os.makedirs('clusters')

  for k in k_values:
    if k > data.shape[0]:
      break

    model = KMeans(init='k-means++', n_clusters=k, max_iter=10000, verbose=0,
                   tol=0.000000001, n_jobs=4)
    model.fit(data)

    sse = 0  # Sum of squared errors.
    centroids = model.cluster_centers_
    labels = model.labels_
    for idx in range(data.shape[0]):
      dist = np.linalg.norm(data[idx] - centroids[labels[idx]])
      sse += dist**2
    mse = sse/data.shape[0]  # Mean squared error.
    mse_sqrt = np.sqrt(mse)
    print str(k) + ': ' + str(model.inertia_) + ': ' + str(mse_sqrt)

    np.save('clusters/centroids_' + str(k) + '.npy', centroids)
    np.save('clusters/labels_' + str(k) + '.npy', labels)

