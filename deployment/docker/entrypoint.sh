#!/bin/bash

service nginx start

chown -R mongodb:mongodb /var/lib/mongodb
service mongodb start

psi-j-testing-service >>/service.log 2>&1
