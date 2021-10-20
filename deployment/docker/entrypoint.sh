#!/bin/bash

service nginx start

chown -R mongodb:mongodb /var/lib/mongodb
service mongodb start

echo "Running testing service..."
psi-j-testing-service 2>&1 | tee -a service.log
