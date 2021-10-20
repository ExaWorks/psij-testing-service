#!/bin/bash

service nginx start

chown -R mongodb:mongodb /var/lib/mongodb
service mongodb start

service psi-j-testing-server start

sleep infinity
