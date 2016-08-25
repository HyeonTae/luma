// Copyright 2016 The Vanadium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

var fs = require('fs');


/**
 * Load the config.json file.
 */
var config;
try {
  config = JSON.parse(fs.readFileSync(__dirname + '/config.json', 'utf8'));
  console.info('Found config.json.');
} catch (ignored) {
  config = {};
  throw new Error('No config file found, please create a config.json.');
}

module.exports = config;
