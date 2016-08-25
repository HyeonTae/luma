// Copyright 2016 The Vanadium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

'use strict';

var config = require('../config');


/**
 * ExpressJS route configuration to serve jade resources as rendered HTML.
 */
module.exports = {
  index: function(req, res) {
    res.render('index', {stfConfig: JSON.stringify(config)});
  },

  modules: function(req, res) {
    var name = req.params.name;
    res.render('modules/' + name);
  }
};
