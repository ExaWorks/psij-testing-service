#!/bin/bash

set -e

error() {
    echo "$@"
    exit 1
}

FORCE=""

if [ "$1" == "--force" ]; then
    FORCE="--force"
fi

if [ ! -f ../config ]; then
    error "This script must be run from the deploy directory"
fi

source ../config

TARGET_VERSION=$1


getId() {
    TYPE=$1
    run docker ps -f "name=service-$TYPE" --format "{{.ID}}"
}

update() {
    TYPE=$1
    ID=`docker ps -f "name=service-$TYPE" --format "{{.ID}}"`
    if [ "$ID" != "" ]; then
        # Make sure everything is up to date
        docker exec -it $ID apt-get update
        docker exec -it $ID apt-get upgrade -y
        # Make sure latest update script is in the container
        docker cp ../docker/update-psi-j-testing-service $ID:/usr/bin
        # Make sure that the latest service script is there
        docker cp ../docker/psi-j-testing-service $ID:/etc/init.d
        # Also make sure that all files are there if needed
        docker cp ../docker/fs/* $ID:/tmp/fs/
        if [ "$DEV" == "1" ]; then
            pushd ../..
            python setup.py sdist
            popd
            docker cp ../../dist/$PACKAGE_NAME-$SERVICE_VERSION.tar.gz $ID:/tmp/$PACKAGE_NAME-$SERVICE_VERSION.tar.gz
            docker exec -it $ID update-psi-j-testing-service $FORCE --src /tmp/$PACKAGE_NAME-$SERVICE_VERSION.tar.gz $TYPE $TARGET_VERSION
        else
            # Actual update
            docker exec -it $ID update-psi-j-testing-service $FORCE $TYPE $TARGET_VERSION
        fi
    else
        echo "Service $TYPE not running."
    fi
}

update psij
update sdk