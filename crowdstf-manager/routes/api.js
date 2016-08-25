// Copyright 2016 The Vanadium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

'use strict';

var request = require('request');
var fs = require('fs');
var uuid = require('node-uuid');
var config = require('../config');
var pollingService = require('../services/pollingService');
var stfService = require('../services/stfService');


/**
 * RESTful ExpressJS route configuration.
 * @param {object} app - an Express app instance.
 */
var apiRouter = function(app) {
  app.get('/api/devices', function(req, res) {
    stfService.getDevices(function(err, devices) {
      if (err) {
        console.error('Error fetching devices', err);
        res.status(500);
        return res.send(err);
      }

      res.send(devices);
    });
  });

  app.get('/api/apps', function(req, res) {
    stfService.getAppList(function(err, appList) {
      if (err) {
        console.error('Error fetching apps', err);
        res.status(500);
        return res.send(err);
      }

      res.send(appList);
    });
  });

  app.post('/api/apps', function(req, res) {
    stfService.saveAppList(req.body, function(err) {
      if (err) {
        console.error('Error saving apps', err);
        res.status(500);
        return res.send(err);
      }

      res.send(200);
    });
  });

  app.delete('/api/apps', function(req, res) {
    stfService.deleteAppList(function(err) {
      if (err) {
        console.error('Error deleting apps', err);
        res.status(500);
        return res.send(err);
      }

      res.send(200);
    });
  });

  app.get('/api/tokens', function(req, res) {
    if (req.query.serial) {
      stfService.generateToken(req.query.serial, req.query.expireMinutes,
          function(err, tokenObj) {
            if (err) {
              console.error('Error generating token', err);
              res.status(500);
              return res.send(err);
            }

            res.send(tokenObj.token);
          });
    } else {
      stfService.getTokens(function(err, tokens) {
        if (err) {
          console.error('Error fetching tokens', err);
          res.status(500);
          return res.send(err);
        }

        res.send(tokens);
      });
    }
  });

  app.delete('/api/tokens/:token', function(req, res) {
    stfService.deleteToken(req.params.token, function(err) {
      if (err) {
        console.error('Error deleting token', err);
        res.status(500);
        return res.send(err);
      }

      res.send(200);
    });
  });

  app.get('/api/polling/start', function(req, res) {
    pollingService.start();
    res.send(200);
  });

  app.get('/api/polling/stop', function(req, res) {
    pollingService.stop();
    res.send(200);
  });

  app.get('/api/polling/status', function(req, res) {
    res.send(pollingService.isActive());
  });
};

module.exports = apiRouter;
