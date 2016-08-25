// Copyright 2016 The Vanadium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

'use strict';


/**
 * REST and websocket data management.
 */
var serviceModule = angular.module('crowdStfManager.services', []);


/**
 * Create a socket communication instance.
 */
serviceModule.factory('socket', function(socketFactory) {
  return socketFactory();
});


/**
 * Create a REST API communication instance.
 */
serviceModule.factory('api', function($http) {
  var api = {};

  /**
   * Fetch the android device list.
   * @return {Promise}
   */
  api.getDevices = function() {
    return $http.get('/api/devices');
  };

  /**
   * Fetch the token list.
   * @return {Promise}
   */
  api.getTokens = function() {
    return $http.get('/api/tokens');
  };

  /**
   * Request a new token.
   * @param {String} serial - device serial.
   * @param {Number} expireMinutes - time until token expires after it's
   * activated.
   * @return {Promise}
   */
  api.generateToken = function(serial, expireMinutes) {
    return $http.get('/api/tokens?serial=' + serial + '&expireMinutes=' +
        expireMinutes);
  };

  /**
   * Expire a token.
   * @return {Promise}
   */
  api.expireToken = function(token) {
    return $http.delete('/api/tokens/' + token);
  };

  /**
   * Fetch the list of apps.
   * @return {Promise}
   */
  api.getAppList = function() {
    return $http.get('/api/apps');
  };

  /**
   * Save a new list of apps.
   * @param {Array} appList - a list of apps.
   * @return {Promise}
   */
  api.setAppList = function(appList) {
    return $http.post('/api/apps', appList);
  };

  /**
   * Delete the list of apps.
   * @return {Promise}
   */
  api.clearAppList = function() {
    return $http.delete('/api/apps');
  };

  /**
   * Request a polling start.
   * @return {Promise}
   */
  api.startPolling = function() {
    return $http.get('/api/polling/start');
  };

  /**
   * Request a polling stop.
   * @return {Promise}
   */
  api.stopPolling = function() {
    return $http.get('/api/polling/stop');
  };

  /**
   * Fetch the polling status.
   * @return {Promise}
   */
  api.getPollingStatus = function() {
    return $http.get('/api/polling/status');
  };

  return api;
});
