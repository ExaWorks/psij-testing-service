FROM ubuntu:20.04

ARG SERVICE_VERSION
ARG GIT_BASE=https://github.com/ExaWorks/psi-j-testing-service/archive/refs/tags

RUN useradd -ms /bin/bash testsrv

RUN apt-get update
RUN apt-get upgrade -y

RUN DEBIAN_FRONTEND="noninteractive" TZ="UTC" apt-get install -y python3.9 python3-pip mongodb wget mc

WORKDIR ~/

RUN pip install $GIT_BASE/v$SERVICE_VERSION.tar.gz

COPY psi-j-testing-service /etc/init.d
COPY entrypoint.sh /
COPY update-psi-j-testing-service /usr/bin
RUN mkdir /var/log/psi-j-testing-service
RUN chown testsrv:testsrv /var/log/psi-j-testing-service

CMD /entrypoint.sh