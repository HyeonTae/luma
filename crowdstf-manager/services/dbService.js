// Copyright 2016 The Vanadium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

'use strict';

var r = require('rethinkdb');
var config = require('../config');


/**
 * Provide connectivity to RethinkDB.
 * @param {function} [onConnect] - An immediate on-connect callback.
 * @return {object} [db] - A db connect instance.
 */
module.exports = function(onConnect) {
  var db = {
    r: r,
    conn: null
  };

  r.connect({
    host: config.database.host,
    port: config.database.port,
    db: config.database.name
  }, function(err, connection) {
    if (err) {
      // Halt the application, this is critical.
      throw Error('Error connecting to database, please check db config.', err);
    }

    db.conn = connection;

    if (onConnect) {
      onConnect(r, db.conn);
    }
  });

  return db;
};
