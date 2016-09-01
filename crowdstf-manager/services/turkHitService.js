// Copyright 2016 The Vanadium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

'use strict';

var mturk = require('mturk-api');
var fs = require('fs');
var jade = require('jade');
var config = require('../config');
var taskTemplate = fs.readFileSync('./views/task.jade', 'utf8');

var jadeTemplate = jade.compile(taskTemplate);

const XML_PREFIX = '<?xml version="1.0"?>\n';
const STF_MAX_HITS_PER_TOKEN = 1;



/**
 * A service for creating hits on mturk.
 * @param {Object} awsCreds - accessKey, secretKey for Amazon Web Services.
 * @constructor
 */
function TurkHitService(awsCreds) {
  if (!awsCreds || !awsCreds.accessKey || !awsCreds.secretKey) {
    throw 'Missing AWS creds. Please add to config.json.';
  }

  if (!config.hit || !config.hit.productionQual) {
    throw 'Missing hit details. Please add to config.json.';
  }

  this.turkCredObj = {
    access: awsCreds.accessKey,
    secret: awsCreds.secretKey,
    sandbox: !config.production
  };

  if (config.production) {
    console.info('Production environment detected. HITs will be created in ' +
        'turk production.');
  } else {
    console.info('Development environment detected. HITs will be created in ' +
        'turk sandbox.');
  }

  this.activePolling = false;
}


/**
 * Post a HIT on mturk.
 * @param {string} token - an STF access token.
 * @param {number} taskMinutes - minutes until token expires after activated.
 * @param {string} appName - name of android app to be launched on task start.
 * @param {function} callback - method triggered when requests are complete.
 */
TurkHitService.prototype.createHit = function(token, taskMinutes, appName,
                                              callback) {
  if (!token) {
    callback('Missing required token for HIT.');
    return;
  }
  if (!taskMinutes) {
    callback('Missing required task minutes for HIT.');
    return;
  }
  if (!appName) {
    callback('Missing required app name for HIT.');
    return;
  }

  var hitTitle = config.hit.title.replace(/%s/g, taskMinutes);
  var rewardPrice = taskMinutes * config.hit.rewardDollarsPerMinute;
  var hitHTML = jadeTemplate({
    token: token,
    tokenUrl: config.stfAuthUrl + '/auth/token/' + token,
    taskTime: taskMinutes,
    appName: appName,
    contactEmail: config.hitAccounts.contactEmail,
    logins: config.hitAccounts.logins,
    taskScreenShot: config.taskScreenShot
  });

  var hitConfig = {
    Title: hitTitle,
    Question: XML_PREFIX + hitHTML,
    Keywords: config.hit.keywords,
    Description: config.hit.description,
    MaxAssignments: STF_MAX_HITS_PER_TOKEN,
    LifetimeInSeconds: config.hit.lifetimeInSeconds,
    AssignmentDurationInSeconds: config.hit.assignmentDurationInSeconds,
    AutoApprovalDelayInSeconds: config.hit.autoApprovalDelayInSeconds,
    QualificationRequirement: config.production ? [config.hit.productionQual] :
        [config.hit.sandboxQual],
    Reward: {
      Amount: rewardPrice,
      CurrencyCode: config.hit.currencyCode,
      FormattedPrice: config.hit.currencyPrefix + rewardPrice
    }
  };

  mturk.connect(this.turkCredObj).then(function(turkApi) {
    turkApi.req('CreateHIT', hitConfig).then(function(res) {
      try {
        var hitId = res.HIT[0].HITId[0];
      } catch (err) {
        return callback(err);
      }

      var env = config.production ? 'production' : 'sandbox';
      console.info('Created turk ' + env + ' HIT, returned ID:', hitId);
      callback(null, hitId);
    }, function(err) {
      return callback(err);
    });
  }).catch(function(err) {
    return callback(err);
  });
};

var turkHitService = new TurkHitService(config.awsCreds);
module.exports = turkHitService;
