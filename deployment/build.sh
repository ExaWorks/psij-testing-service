#!/bin/bash

VERSION=`cat ../RELEASE`

echo "Version: $VERSION"


docker build --build-arg SERVICE_VERSION=$VERSION -t hategan/psi-j-testing-service:$VERSION .
docker push hategan/psi-j-testing-service:$VERSION
