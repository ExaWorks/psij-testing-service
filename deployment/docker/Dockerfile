FROM ubuntu:20.04

ARG SERVICE_PACKAGE

RUN useradd -ms /bin/bash testsrv

RUN apt-get update
RUN apt-get upgrade -y

RUN DEBIAN_FRONTEND="noninteractive" TZ="UTC" apt-get install -y python3.9 python3-pip mongodb \
    wget mc postfix procmail syslog-ng

WORKDIR ~/

# needed to get syslog-ng to work inside the container
RUN sed -i 's/system()/system(exclude-kmsg(yes))/g' /etc/syslog-ng/syslog-ng.conf


COPY $SERVICE_PACKAGE /tmp
RUN pip install /tmp/$SERVICE_PACKAGE
RUN rm /tmp/$SERVICE_PACKAGE

COPY fs /
RUN mkdir /var/log/psi-j-testing-service
RUN chown testsrv:testsrv /var/log/psi-j-testing-service

CMD /entrypoint.sh
