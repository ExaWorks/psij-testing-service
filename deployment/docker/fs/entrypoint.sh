#!/bin/bash

set -e

service syslog-ng start
chown -R mongodb:mongodb /var/lib/mongodb
service mongodb start
service postfix start

service psi-j-testing-service start

sleep infinity
