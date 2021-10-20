#!/bin/bash

INTERACTIVE=0

if [ "$1" == "-i" ]; then
    INTERACTIVE=1
    shift
fi

VERSION=$1

if [ "$VERSION" == "" ]; then
    echo "Version required"
    exit 1
fi

if [ ! -f certs/certs/ssl.crt ]; then
    echo "Missing SSL certificate"
    exit 2
fi


# this is where the database is stored
mkdir -p data

# webroot is for certbot; only serving from the ".well-known" directory
# is configured in nginx.conf
mkdir -p webroot


if [ "$INTERACTIVE" == 1 ]; then
    docker run \
        -i \
        -p 80:80 \
        -p 443:443 \
        --volume=$PWD/data:/var/lib/mongodb \
        --volume=$PWD/webroot:/var/www/html \
        --volume=$PWD/certs:/etc/ssl/exaworks \
        hategan/psi-j-testing-service:$VERSION /bin/bash
else
    docker run \
        -d \
        -p 80:80 \
        -p 443:443 \
        --restart=on-failure:3 \
        --volume=$PWD/data:/var/lib/mongodb \
        --volume=$PWD/webroot:/var/www/html \
        --volume=$PWD/certs:/etc/ssl/exaworks \
        hategan/psi-j-testing-service:$VERSION
fi