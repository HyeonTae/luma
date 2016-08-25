// Copyright 2016 The Vanadium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

'use strict';


/**
 * Setup angular main module and configure HTML5 hash routing.
 */
angular.module('crowdStfManager', [
  'ngRoute',
  'crowdStfManager.controllers',
  'crowdStfManager.services',
  'btford.socket-io'
]).config(function($routeProvider, $locationProvider) {
  $routeProvider.when('/usageStream', {
    templateUrl: 'modules/usageStream',
    controller: 'UsageStreamController'
  }).when('/tokens', {
    templateUrl: 'modules/tokens',
    controller: 'TokenManagerController'
  }).otherwise({
    redirectTo: '/tokens'
  });

  $locationProvider.html5Mode(true);
});
