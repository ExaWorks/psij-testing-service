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
    FQDN=$3
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
        cp $ROOT/web/$TYPE/* $DATA_DIR/$TYPE/web

        run docker run \
            -d -p $PORT:9909 --name "service-$TYPE" -h $FQDN \
            --restart=on-failure:3 \
            --volume=$DATA_DIR/$TYPE/mongodb:/var/lib/mongodb \
            --volume=$DATA_DIR/$TYPE/web:/var/www/html \
            --volume=/etc/letsencrypt:/etc/letsencrypt \
            $EXTRA_VOL \
            $IMAGE:$SERVICE_VERSION
        UPDATE_CONTAINER=1
        getId $TYPE
        ID=$OUT
        run docker exec -it $ID bash -c "echo $FQDN > /etc/hostname"
        if [ ! -f ../docker/fs/etc/psij-testing-service/secrets.json ]; then
            error "No secrets.json found. Please edit/create secrets.json in ../docker/fs/etc/psij-testing-service"
        fi
        run docker cp ../docker/fs/. $ID:/
        run docker exec -it $ID bash -c "pip show $PACKAGE_NAME | grep 'Location: ' | sed 's/Location: //' | tr -d '\n'"
        PACKAGE_LOC=$OUT
        run docker cp ../web/. "$ID:$PACKAGE_LOC/psij/web/"
    fi
    if [ "$UPDATE_CONTAINER" != "0" ]; then
        if [ "$DEV" == "1" ]; then
            ./upgrade.sh -y --force --component $TYPE /psi-j-testing-service-dev
        else
            ./upgrade.sh -y --force --component $TYPE $SERVICE_VERSION
        fi
    fi
}


if service nginx status >/dev/null 2>&1; then
    echo "Nginx is already running. Skipping deployment."
    UPDATE_NGINX=$FORCED_UPDATE
else
    if [ "$USER" != "root" ]; then
        error "You need root permissions to run this script."
    fi

    run apt-get update
    run apt-get install -y nginx
    UPDATE_NGINX=1
fi

filterConf() {
    SRC="$1"
    DST="$2"
    SERVER_NAME="$3"
    PROXY_REDIRECT="$4"
    INTERNAL_PORT="$5"

    if [ -f "$DST" ]; then
        cp "$DST" "$DST.bk"
    fi
    sed -e "s/\${DOMAIN_NAME}/${DOMAIN_NAME}/g" "$SRC" | \
    sed -e "s/\${SERVER_NAME}/${SERVER_NAME}/g" | \
    sed -e "s/\${PROXY_REDIRECT}/${PROXY_REDIRECT}/g" | \
    sed -e "s/\${INTERNAL_PORT}/${INTERNAL_PORT}/g" >"$DST"
}

deploySite() {
    NAME="$1"
    SERVER_NAME="$2"
    PROXY_REDIRECT="$2"
    INTERNAL_PORT="$3"

    echo "Deploying site $NAME"
    filterConf nginx/site-template "/etc/nginx/sites-available/$NAME" "$SERVER_NAME" "$PROXY_REDIRECT" "$INTERNAL_PORT"
    ln -f -s "/etc/nginx/sites-available/$NAME" "/etc/nginx/sites-enabled/$NAME"
}

DOMAIN_NAME=`cat DOMAIN_NAME | tr -d '\n'`

if [ "$UPDATE_NGINX" != "0" ]; then
    filterConf nginx/headers.conf /etc/nginx/snippets/headers.conf
    filterConf nginx/nginx.conf /etc/nginx/nginx.conf
    filterConf nginx/ssl.conf /etc/nginx/ssl.conf

    filterConf nginx/site-default /etc/nginx/sites-available/default
    run ln -f -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

    # psij is default
    deploySite "$DOMAIN_NAME" "psij.$DOMAIN_NAME" 9901
    deploySite "psij.$DOMAIN_NAME" "psij.$DOMAIN_NAME" 9901
    deploySite "sdk.$DOMAIN_NAME" "sdk.$DOMAIN_NAME" 9902

    run service nginx restart
fi

deployContainer psij 9901 "psij.$DOMAIN_NAME"
deployContainer sdk 9902 "sdk.$DOMAIN_NAME"
