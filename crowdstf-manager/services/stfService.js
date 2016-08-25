// Copyright 2016 The Vanadium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

'use strict';

var request = require('request');
var uuid = require('node-uuid');
var _ = require('underscore');
var config = require('../config');
var db = require('./dbService')();
var r = db.r;


/**
 * Service for interaction with CrowdSTF REST API and DB.
 */
var stfService = {

  /**
   * Fetch connected device and merge in their token data.
   * @param {function} callback - method triggered when requests are complete.
   */
  getDevices: function(callback) {
    var stfDeviceUrl = config.stfAppUrl + '/app/api/v1/devices?authed=true';

    request(stfDeviceUrl, function(err, res, json) {
      if (err || res.statusCode !== 200) {
        return callback(err || res.statusCode);
      }

      try {
        var devices = JSON.parse(json).devices;
      } catch (err) {
        return callback(err);
      }

      stfService.getTokens(function(err, tokens) {
        if (err) {
          return callback(err);
        }

        _(devices).each(function(device) {
          var foundToken = _(tokens).find(function(token) {
            return token.serial === device.serial &&
                token.status !== 'expired';
          });

          if (foundToken) {
            device.token = foundToken.token;
            device.tokenStatus = foundToken.status;
          }
        });

        callback(null, devices);
      });
    });
  },

  /**
   * Fetch all apps.
   * @param {function} callback - method triggered when requests are complete.
   */
  getAppList: function(callback) {
    r.table('deviceApps').run(db.conn, function(err, cursor) {
      if (err) {
        return callback(err);
      }

      cursor.toArray(function(err, appList) {
        if (err) {
          return callback(err);
        }

        callback(null, appList);
      });
    });
  },

  /**
   * Save a new list of apps.
   * @param {Array<Object>} - a list of app objects.
   * @param {function} callback - method triggered when requests are complete.
   */
  saveAppList: function(appList, callback) {
    if (!appList || !appList.length) {
      callback('Error: cannot save an empty or missing app list.');
      return;
    }

    var unusedApps = _(appList).map(function(appId) {
      return {appId: appId, used: false};
    });

    r.table('deviceApps').insert(unusedApps, {
      conflict: 'error'
    }).run(db.conn, function(err, res) {
      if (err) {
        return callback(err);
      }

      callback(null, res);
    });
  },

  /**
   * Delete all apps.
   * @param {function} callback - method triggered when requests are complete.
   */
  deleteAppList: function(callback) {
    r.table('deviceApps').delete().run(db.conn, function(err, res) {
      if (err) {
        return callback(err);
      }

      callback(null, res);
    });
  },

  /**
   * Get all tokens.
   * @param {function} callback - method triggered when requests are complete.
   */
  getTokens: function(callback) {
    r.table('tokens').run(db.conn, function(err, cursor) {
      if (err) {
        return callback(err);
      }

      cursor.toArray(function(err, results) {
        if (err) {
          return callback(err);
        }

        callback(null, results);
      });
    });
  },

  /**
   * Delete a token via the STF API. STF will force-kick devices when
   * receiving this request.
   * @param {string} token - an STF access token.
   * @param {function} callback - method triggered when requests are complete.
   */
  deleteToken: function(token, callback) {
    var appDeleteUrl = config.stfAppUrl + '/app/api/v1/token/' + token +
        '?authed=true';

    request.delete(appDeleteUrl, function(err, res) {
      if (err) {
        return callback(err);
      }

      callback(null, res);
    });
  },

  /**
   * Create a token for a device by verifying a device does not already
   * have a token and that a free app is available to launch. Assign the
   * app and device serial to the token and save it.
   * @param {string} serial - a device serial.
   * @param {number} expireMinutes - minutes until token expires after it is
   * activated.
   * @param {function} callback - method triggered when requests are complete.
   */
  generateToken: function(serial, expireMinutes, callback) {
    // Check if there are already tokens for the serial.
    r.table('tokens').filter({
      serial: serial,
      status: 'unused'
    }).run(db.conn, function(err, cursor) {
      if (err) {
        return callback(err);
      }

      cursor.toArray(function(err, results) {
        if (err) {
          return callback(err);
        }

        if (results.length > 1) {
          // Halt execution, because a device should never have multiple tokens.
          throw 'Multiple unused tokens detected for device: ' + serial;
        }

        if (results.length === 1) {
          // Return the token already allocated for the device.
          return callback(null, results[0]);
        }

        // Get an unused app for the token; mark it as used in one transaction.
        r.table('deviceApps').filter({
          used: false
        }).limit(1).update({
          used: true,
          updated: new Date().getTime()
        }, {
          returnChanges: true
        }).run(db.conn, function(err, res) {
          if (err) {
            return callback(err);
          }

          if (!res.changes || !res.changes.length || !res.changes[0].new_val) {
            return callback('There are no apps remaining for new tokens.');
          }

          // Get the updated version of the app record for the token
          var app = res.changes[0].new_val;

          try {
            expireMinutes = parseFloat(expireMinutes);
          } catch (ignored) {
            expireMinutes = 5.0;
          }

          var tokenObj = {
            token: uuid.v4(),
            appId: app.appId,
            serial: serial,
            status: 'unused',
            creationTime: Date.now(),
            expireMinutes: expireMinutes
          };

          r.table('tokens').insert(tokenObj).run(db.conn, function(err) {
            if (err) {
              return callback(err);
            }

            callback(null, tokenObj);
          });
        });
      });
    });
  }
};

module.exports = stfService;
