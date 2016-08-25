// Copyright 2016 The Vanadium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

'use strict';

const MILLIS_PER_SEC = 1000;
var controllerModule = angular.module('crowdStfManager.controllers', []);


/**
 * Controls UI interaction with the Usage Stream view.
 * @class crowdStfManager.UsageStreamController
 */
controllerModule.controller('UsageStreamController', function($scope, socket) {
  $scope.slider = 0;
  $scope.deviceEvents = [];

  socket.on('deviceEvent', function(data) {
    $scope.deviceEvents.unshift(JSON.parse(data.deviceEvent));
  });
});


/**
 * Controls UI interaction with the Token Manager view.
 * @class crowdStfManager.TokenManagerController
 */
controllerModule.controller('TokenManagerController', function($scope, api) {
  $scope.serialExpires = {};
  $scope.pendingAppList = [];
  $scope.appList = [];
  $scope.stfAuthUrl = window.stfConfig.stfAuthUrl;

  var syncApps = function() {
    api.getAppList().then(function(res) {
      $scope.appList = res.data;
    }, function(err) {
      console.error('Error fetching app list', err);
    });
  };

  var syncTokens = function() {
    api.getTokens().then(function(res) {
      $scope.tokens = res.data;
    }, function(err) {
      console.error('Error fetching tokens', err);
    });
  };

  var syncDevices = function() {
    api.getDevices().then(function(res) {
      $scope.devices = res.data;
    }, function(err) {
      console.error('Error fetching devices', err);
    });
  };

  var syncPolling = function() {
    api.getPollingStatus().then(function(res) {
      $scope.activePolling = res.data === 'true';
    }, function(err) {
      console.error('Error fetching polling status', err);
    });
  };

  $scope.startPolling = function() {
    api.startPolling().then(syncPolling, function(err) {
      console.error('Error starting polling', err);
    });
  };

  $scope.stopPolling = function() {
    api.stopPolling().then(syncPolling, function(err) {
      console.error('Error stopping polling', err);
    });
  };

  $scope.setAppList = function() {
    api.setAppList($scope.pendingAppList).then(function() {
      $scope.pendingAppList = [];
      syncApps();
    }, function(err) {
      console.error('Error setting new app list', err);
    });
  };

  $scope.clearAppList = function() {
    api.clearAppList().then(syncApps, function(err) {
      console.error('Error clearing app list', err);
    });
  };

  $scope.generateToken = function(serial) {
    var expireMinutes = $scope.serialExpires[serial];
    api.generateToken(serial, expireMinutes).then(function() {
      syncDevices();
      syncTokens();
    }, function(err) {
      console.error('Error generating token', err);
    });
  };

  $scope.expireToken = function(token) {
    api.expireToken(token).then(function() {
      syncTokens();
      syncDevices();
    }, function(err) {
      console.error('Error expiring token', err);
    });
  };

  $scope.sync = function(delaySeconds) {
    if (delaySeconds) {
      return setTimeout($scope.sync, delaySeconds * MILLIS_PER_SEC);
    }
    syncDevices();
    syncTokens();
    syncApps();
    syncPolling();
  };

  $scope.sync();
});
