FROM ubuntu:20.04

ARG SERVICE_VERSION
ARG GIT_BASE=https://github.com/ExaWorks/psi-j-testing-service/archive/refs/tags


RUN apt-get update
RUN apt-get upgrade

RUN DEBIAN_FRONTEND="noninteractive" TZ="UTC" apt-get install -y python3.9 python3-pip mongodb nginx mc

WORKDIR ~/

RUN pip install $GIT_BASE/v$SERVICE_VERSION.tar.gz

COPY nginx.conf /etc/nginx
COPY entrypoint.sh /

CMD /entrypoint.sh