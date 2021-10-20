FROM ubuntu:20.04

ARG SERVICE_VERSION
ARG GIT_BASE=https://github.com/ExaWorks/psi-j-testing-service/archive/refs/tags

RUN useradd -ms /bin/bash testsrv

RUN apt-get update
RUN apt-get upgrade

RUN DEBIAN_FRONTEND="noninteractive" TZ="UTC" apt-get install -y python3.9 python3-pip mongodb nginx mc

WORKDIR ~/

RUN pip install $GIT_BASE/v$SERVICE_VERSION.tar.gz

COPY nginx.conf /etc/nginx
COPY psi-j-testing-service /etc/init.d
COPY entrypoint.sh /
RUN mkdir /var/log/psi-j-testing-service
RUN chown testsrv:testsrv /var/log/psi-j-testing-service

CMD /entrypoint.sh