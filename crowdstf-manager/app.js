// Copyright 2016 The Vanadium Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

'use strict';


/**
 * Node start script.
 * Start Express, configure its routes, and setup websocket connectivity.
 */
var http = require('http');
var path = require('path');
var config = require('./config');
var express = require('express');
var socket = require('socket.io');
var routes = require('./routes');
var apiRoutes = require('./routes/api');
var socketRoutes = require('./routes/socket');

var app = express();
var server = http.createServer(app);
var io = socket.listen(server, {log: false});

app.set('port', config.port || 3000);
app.set('views', __dirname + '/views');
app.set('view engine', 'jade');

app.use(express.bodyParser());
app.use(express.methodOverride());
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.static(path.join(__dirname, './screen_shots')));
app.use(app.router);

app.get('/', routes.index);
app.get('/modules/:name', routes.modules);
apiRoutes(app);

app.get('*', routes.index);

io.sockets.on('connection', socketRoutes);

server.listen(app.get('port'), function() {
  console.log('STF Manager listening on port ' + app.get('port') + '.');
});
