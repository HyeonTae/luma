# CrowdSTF Manager

Manage CrowdSTF devices, tokens, and hit allocation from a web UI. Visualize device streams from CrowdSTF in real-time.

### Project Structure

- app.js - the application start script
- config.json - a required configuration file (see config-example.json)
- package.json - node back-end library dependency config
- bower.json - node front-end library dependency config
- public/ - static resources made available to web clients
    - js/ - javascripts
        - app - angular module config and route config
        - controllers - angular web UI scope implementation
        - services.js - http and websocket data
    - css/ - style sheets
- routes/ - web facing URI implementation
    - api - REST api routes
    - index - root web routes
    - socket - websocket emitter
- services/ - data service implementation
    - dbService - manages db connections
    - pollingService - manages device polling and automated HIT creation
    - stfService - manages CrowdSTF data
    - turkHitService - manages HIT creation
- views - jade templates for creating HTML views
    - modules/ - refreshless modules for the index route
        - tokens.jade
        - usageStream.jade
    - index.jade - main site view
    - layout.jade - boilerplate layout
    - task.jade - turk task (changes to this will appear on turk hits)

## Installation

Install [CrowdSTF](https://github.com/vanadium/luma.third_party/tree/master/crowdstf) and its dependencies.

Install NodeJS from [nodejs.org](http://nodejs.org/download/) or [node version manager](https://github.com/creationix/nvm). Supported version is node v4.1.2.

Verify the node version

    node --version  #should read v4.1.2

Install the npm dependencies

    # at the project root
    npm install

Install the bower dependencies

    # at the project root
    bower install

Create a config.json

    # at the project root
    cp config-example.json config.json
    # remove comments and configure

### Launching CrowdSTF Manager

Start RethinkDB

    rethinkdb --directory ./rethinkdb_data/

Launch CrowdSTF Manager

    node app.js
