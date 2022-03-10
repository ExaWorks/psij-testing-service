#!/bin/bash

error() {
    echo "$@"
    exit 1
}

if [ ! -f ../config ]; then
    error "This script must be run from docker directory"
fi

source ../config

echo "Version: $VERSION"


docker build --build-arg SERVICE_VERSION=$SERVICE_VERSION --build-arg GIT_BASE="$GIT_BASE" -t $IMAGE:$VERSION .
docker push $IMAGE:$VERSION
docker image tag $IMAGE:$VERSION $IMAGE:latest
docker push $IMAGE:latest
