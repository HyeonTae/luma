// Copyright 2016 The Vanadium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

'use strict';

var db = require('../services/dbService');
var config = require('../config');


/**
 * Configure websocket router to emit events.
 * @param {object} socket - a SocketIO instance.
 */
module.exports = function(socket) {
  // Check if the broadcast event feature is enabled. If not, return before
  // installing a database listener for device events. Enabling this has a
  // heavy performance impact.
  if (!config.broadcastEvents) {
    console.info('Frame broadcasting is deactivated based on config.');
    return;
  }

  db(function(r, conn) {
    r.table('deviceEvents').changes().run(conn, function(err, cursor) {
      if (err) {
        return console.error('Error listening for device event changes', err);
      }

      cursor.each(function(err, data) {
        if (!data) {
          return;
        }

        // Forward all new device events to the UI over websockets.
        socket.emit('deviceEvent', {
          deviceEvent: JSON.stringify(data.new_val, null, 2)
        });
      });
    });
  });
};
