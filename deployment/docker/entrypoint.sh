#!/bin/bash

service nginx start

chown -R mongodb:mongodb /var/lib/mongodb
service mongodb start

service psi-j-testing-service start

sleep infinity
