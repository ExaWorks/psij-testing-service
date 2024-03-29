#!/bin/bash

set -e

error() {
    echo "$@"
    exit 1
}

usage() {
    echo "Usage:"
    echo "    upgrade.sh [-h|--help] [-f|--force] [-c | --component] [-y | --assume-yes]"
    exit 1
}


FORCE=""
DONTASK=""
COMPONENTS="psij sdk"
DOMAIN_NAME=`cat DOMAIN_NAME | tr -d '\n'`

while [ "$1" != "" ]; do
    case "$1" in
        -h | --help)
            usage
            ;;
        -f | --force)
            FORCE="--force"
            shift
            ;;
        -y | --assume-yes)
            DONTASK="-y"
            shift
            ;;
        -c | --component)
            COMPONENTS="$2"
            shift
            shift
            ;;
        *)
            TARGET_VERSION=$1
            shift
            ;;
    esac
done

if [ ! -f ../config ]; then
    error "This script must be run from the deploy directory"
fi

source ../config


getId() {
    TYPE=$1
    docker ps -f "name=service-$TYPE" --format "{{.ID}}"
}

update() {
    TYPE=$1
    ID=`docker ps -f "name=service-$TYPE" --format "{{.ID}}"`
    if [ -f DOMAIN_NAME.$TYPE ]; then
        LOCAL_DN=`cat DOMAIN_NAME.$TYPE | tr -d '\n'`
    else
        LOCAL_DN=$DOMAIN_NAME
    fi
    if [ "$ID" != "" ]; then
        # Make sure everything is up to date
        docker exec -it $ID apt-get update
        docker exec -it $ID apt-get upgrade -y
        # Make sure that all files are there if needed
        # We need root because some files contain secrets which are 600 and owned by root
        sudo docker cp ../docker/fs/. $ID:/tmp/fs/
        if [ -d ../docker/fs.$TYPE ]; then
            docker cp ../docker/fs.$TYPE/. $ID:/tmp/fs/
        fi
        docker cp ../web/. "$ID:/tmp/web/"
        docker exec -it $ID bash -c "echo $TYPE.$LOCAL_DN > /etc/hostname"
        # Ensure we have the latest update script before calling it
        docker cp ../docker/fs/usr/bin/update-psi-j-testing-service $ID:/usr/bin
        if [ "$DEV" == "1" ]; then
            pushd ../..
            python setup.py sdist
            popd
            docker cp ../../dist/$PACKAGE_NAME-$SERVICE_VERSION.tar.gz $ID:/tmp/$PACKAGE_NAME-$SERVICE_VERSION.tar.gz
            docker exec -it $ID update-psi-j-testing-service $DONTASK $FORCE --src /tmp/$PACKAGE_NAME-$SERVICE_VERSION.tar.gz $TYPE $TARGET_VERSION
        else
            # Actual update
            docker exec -it $ID update-psi-j-testing-service $DONTASK $FORCE $TYPE $TARGET_VERSION
        fi
    else
        echo "Service $TYPE not running."
    fi
}


for COMPONENT in $COMPONENTS; do
    update $COMPONENT
done
