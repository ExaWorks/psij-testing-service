#!/bin/bash

set -e

error() {
    echo "$@"
    exit 1
}

if [ ! -f ../config ]; then
    error "This script must be run from docker directory"
fi

source ../config

echo "Version: $VERSION"

if [ "$DEV" == "1" ]; then
    pushd ../..
    python setup.py sdist
    popd
    cp ../../dist/$PACKAGE_NAME-$SERVICE_VERSION.tar.gz ./$PACKAGE_NAME-$SERVICE_VERSION.tar.gz
else
    wget $GIT_BASE/v$SERVICE_VERSION.tar.gz -O ./$PACKAGE_NAME-$SERVICE_VERSION.tar.gz
fi


docker build --build-arg SERVICE_PACKAGE=./$PACKAGE_NAME-$SERVICE_VERSION.tar.gz -t $IMAGE:$VERSION .
docker image tag $IMAGE:$VERSION $IMAGE:latest
if [ "$DEV" == "0" ]; then
    docker push $IMAGE:$VERSION
    docker push $IMAGE:latest
fi
