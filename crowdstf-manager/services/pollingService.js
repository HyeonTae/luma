// Copyright 2016 The Vanadium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

'use strict';

var _ = require('underscore');
var stfService = require('../services/stfService');
var turkHitService = require('../services/turkHitService');
var config = require('../config');

const POLL_INTERVAL = config.pollIntervalMillis || 15000;
const TASK_MINS = config.polledTaskMinutes || 5.0;



/**
 * PollingService polls devices and issues tokens based on availability.
 * @constructor
 */
function PollingService() {
  this.activePolling = false;
}


/**
 * Starts the polling interval.
 */
PollingService.prototype.start = function() {
  if (pollingService.activePolling) {
    return;
  }

  pollingService.activePolling = true;
  pollingService.poll();
};


/**
 * Stops the polling interval.
 */
PollingService.prototype.stop = function() {
  pollingService.activePolling = false;
};


/**
 * Reports the polling interval status.
 * @return {Boolean} activePolling - the polling status.
 */
PollingService.prototype.isActive = function() {
  return pollingService.activePolling;
};


/**
 * Polls for available devices who don't have tokens assigned to them.
 */
PollingService.prototype.poll = function() {
  if (!pollingService.isActive()) {
    return;
  }

  stfService.getTokens(function(err, tokens) {
    if (err) {
      console.error('Error getting tokens', err);
      return pollingService.stop();
    }

    var unusedTokens = _(tokens).filter(function(token) {
      return token.status === 'unused' || token.status === 'active';
    });

    stfService.getDevices(function(err, devices) {
      if (err) {
        console.error('Error getting devices', err);
        return pollingService.stop();
      }

      var presentDevices = _(devices).filter(function(device) {
        return device.present;
      });

      var unusedDevices = _(presentDevices).filter(function(presentDevice) {
        return !presentDevice.token;
      });

      if (unusedTokens.length >= presentDevices.length) {
        return setTimeout(pollingService.poll, POLL_INTERVAL);
      }

      if (unusedDevices.length > 0) {
        pollingService.allocateTokens(unusedDevices);
      } else {
        return setTimeout(pollingService.poll, POLL_INTERVAL);
      }
    });
  });
};


/**
 * Assigns tokens to devices and issues HITs for the tokens.
 * @param {Array<Object>} unusedDevices  - list of free device objects
 */
PollingService.prototype.allocateTokens = function(unusedDevices) {
  var tokens = [];

  var getToken = function(device) {
    console.info('Generating token for device:', device.serial);

    stfService.generateToken(device.serial, TASK_MINS, function(err, tokenObj) {
      if (err) {
        console.error('Error generating token', err);

        // Continue with the rest despite the error.
        if (unusedDevices.length) {
          return getToken(unusedDevices.pop());
        }

        // If we didn't issue tokens, return to polling.
        if (!tokens.length) {
          return setTimeout(pollingService.poll, POLL_INTERVAL);
        }
      } else {
        tokens.push(tokenObj);
      }

      if (unusedDevices.length) {
        return getToken(unusedDevices.pop());
      } else {
        var createHit = function(tk) {
          turkHitService.createHit(tk.token, TASK_MINS, tk.appId,
              function done(err) {
                if (err) {
                  console.error('Error creating hit', err);

                  // Fallback and undo token allocation.
                  stfService.deleteToken(tk.token, function(err) {
                    if (err) {
                      console.error('Error deleting token for bad hit', err);
                    } else {
                      console.info('Deleted token for bad HIT');
                    }
                  });

                  // Continue creating HITs.
                  if (tokens.length > 0) {
                    return createHit(tokens.pop());
                  }

                  return setTimeout(pollingService.poll, POLL_INTERVAL);
                }

                if (tokens.length > 0) {
                  createHit(tokens.pop());
                } else {
                  return setTimeout(pollingService.poll, POLL_INTERVAL);
                }
              });
        };

        createHit(tokens.pop());
      }
    });
  };

  getToken(unusedDevices.pop());
};

var pollingService = new PollingService();

module.exports = pollingService;
