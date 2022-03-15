#!/bin/bash

error() {
    echo "$@"
    exit 1
}

if [ ! -f ../config ]; then
    error "This script must be run from the deploy directory"
fi

source ../config
ROOT=`dirname $PWD`
FORCED_UPDATE=0

usage() {
    echo "Usage:"
    echo "    deploy.sh [-h|--help] [-u|--update]"
    exit 1
}

while [ "$1" != "" ]; do
    case "$1" in
        -h | --help)
            usage
            ;;
        -u | --update)
            FORCED_UPDATE=1
            shift
            ;;
        *)
            error "Unrecognized option $1"
            ;;
    esac
done

run() {
    echo -n "Running $@..."
    echo "> $@" >>deploy.log
    OUT=`"$@" 2>&1`
    # `
    if [ "$?" != "0" ]; then
        echo "FAILED"
        echo $OUT
        exit 2
    fi
    echo $OUT >>deploy.log
    echo "DONE"
}

getId() {
    TYPE=$1
    run docker ps -f "name=service-$TYPE" --format "{{.ID}}"
}

deployContainer() {
    TYPE=$1
    PORT=$2
    getId $TYPE
    ID=$OUT
    echo "ID: $OUT"
    if [ "$ID" != "" ]; then
        echo "Existing instance of $TYPE service found. Skipping deployment."
        UPDATE_CONTAINER=$FORCED_UPDATE
    else
        if [ "$DEV" == "1" ]; then
            EXTRA_VOL="--volume=$ROOT/..:/psi-j-testing-service-dev"
        else
            EXTRA_VOL=""
        fi
        mkdir -p $DATA_DIR/$TYPE/mongodb
        mkdir -p $DATA_DIR/$TYPE/web
        run docker run \
            -d -p $PORT:9909 --name "service-$TYPE" \
            --restart=on-failure:3 \
            --volume=$DATA_DIR/$TYPE/mongodb:/var/lib/mongodb \
            --volume=$DATA_DIR/$TYPE/web:/var/www/html \
            $EXTRA_VOL \
            $IMAGE:latest
        UPDATE_CONTAINER=1
    fi
    if [ "$UPDATE_CONTAINER" != "0" ]; then
        getId $TYPE
        ID=$OUT
        if [ "$DEV" == "1" ]; then
            run docker exec -it $ID update-psi-j-testing-service -y /psi-j-testing-service-dev
        else
            run docker exec -it $ID update-psi-j-testing-service -y $SERVICE_VERSION
        fi
    fi
}

if [ "$USER" != "root" ]; then
    error "You need root permissions to run this script."
fi

if service nginx status >/dev/null 2>&1; then
    echo "Nginx is already running. Skipping deployment."
    UPDATE_NGINX=$FORCED_UPDATE
else
    run apt-get update
    run apt-get install -y nginx
    UPDATE_NGINX=1
fi

if [ "$UPDATE_NGINX" != "0" ]; then
    run cp -u nginx.conf /etc/nginx
    run service nginx restart
fi

deployContainer psij 9901
deployContainer sdk 9902
