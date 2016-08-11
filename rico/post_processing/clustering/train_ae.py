# Copyright 2016 The Vanadium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

"""Trains an autoencoder using the Keras and Theano.

This script trains an autoencoder and saves the model and its weights.

"""

import matplotlib.pyplot as plt
import numpy as np

from keras.layers import Input, Dense
from keras.models import Model

NUM_EPOCHS = 120
BATCH_SIZE = 512

if __name__ == '__main__':
  input_img = Input(shape=(16800,))
  encoded1 = Dense(2048, activation='relu')(input_img)
  encoded2 = Dense(256, activation='relu')(encoded1)
  encoded3 = Dense(64, activation='relu')(encoded2)
  decoded1 = Dense(256, activation='relu')(encoded3)
  decoded2 = Dense(2048, activation='relu')(decoded1)
  decoded3 = Dense(16800, activation='sigmoid')(decoded2)

  autoencoder = Model(input=input_img, output=decoded3)
  encoder = Model(input=input_img, output=encoded3)

  autoencoder.compile(optimizer='adadelta', loss='binary_crossentropy')

  data = np.load('ae_inputs.npy')
  print 'Number of Inputs: ' + str(data.shape[0])

  num_test_samples = data.shape[0]/6
  num_train_samples = data.shape[0] - num_test_samples
  x_train_l = data[0:num_train_samples].astype(float)
  x_test_l = data[num_train_samples:].astype(float)
  x_all_l = data.astype(float)

  x_train = x_train_l/255.0
  x_test = x_test_l/255.0
  x_all = x_all_l/255.0

  autoencoder.fit(x_train, x_train,
                  nb_epoch=NUM_EPOCHS,
                  batch_size=BATCH_SIZE,
                  shuffle=True,
                  validation_data=(x_test, x_test))

  # Serialize model to JSON.
  model_json = autoencoder.to_json()
  with open('model.json', 'w') as json_file:
    json_file.write(model_json)
  # Serialize weights to HDF5
  autoencoder.save_weights('model.h5', overwrite=True)
  print 'Saved model to disk'

  print 'Computing encodings for images ...'
  encoded_imgs = encoder.predict(x_all)
  print 'Reconstructing images from encoding ...'
  decoded_imgs = autoencoder.predict(x_all)
  np.save('encoded_imgs.npy', encoded_imgs)
  np.save('decoded_imgs.npy', decoded_imgs)
  print 'Saved encodings and reconstructions to disk.'




