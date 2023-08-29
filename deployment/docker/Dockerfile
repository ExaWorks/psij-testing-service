FROM ubuntu:20.04

ARG SERVICE_PACKAGE

RUN useradd -ms /bin/bash testsrv

RUN apt-get update
RUN apt-get upgrade -y

RUN DEBIAN_FRONTEND="noninteractive" TZ="UTC" apt-get install -y python3.9 python3-pip mongodb wget mc postfix

WORKDIR ~/

COPY $SERVICE_PACKAGE /tmp
RUN pip install /tmp/$SERVICE_PACKAGE
RUN rm /tmp/$SERVICE_PACKAGE

COPY psi-j-testing-service /etc/init.d
COPY entrypoint.sh /
COPY update-psi-j-testing-service /usr/bin
RUN mkdir /etc/psij-testing-service
COPY fs/* /
RUN mkdir /var/log/psi-j-testing-service
RUN chown testsrv:testsrv /var/log/psi-j-testing-service

CMD /entrypoint.sh