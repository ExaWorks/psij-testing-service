#!/bin/bash

error() {
    echo "$@"
    exit 1
}

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
        docker exec -it $ID update-psi-j-testing-service $TARGET_VERSION
    else
        echo "Service $TYPE not running."
    fi
}

update psij
update sdk