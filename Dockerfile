FROM ubuntu:18.04
MAINTAINER Santhosh Sundararaman

RUN apt-get update
RUN apt-get -y install build-essential
RUN apt-get -y install libssl-dev
RUN apt-get -y install curl
RUN apt-get -y install vim
RUN apt-get -y install net-tools
RUN apt-get -y install supervisor
RUN apt-get -y install python-minimal python-dev python-setuptools python-pip
RUN apt-get -y install nodejs npm

RUN npm install -g @google-cloud/functions-emulator

ADD requirements.txt /tmp/pip-install/

WORKDIR /tmp/pip-install

RUN pip install -r requirements.txt
RUN rm -fr /tmp/pip-install

# Setup supervisord
COPY supervisor.conf /etc/supervisor.d/

ADD config.json /root/.config/configstore/\@google-cloud/functions-emulator/config.json
ADD functions-start.sh /root

ADD ./api /api

EXPOSE 8010/tcp
EXPOSE 8008/tcp
EXPOSE 90/tcp

WORKDIR /

#ENTRYPOINT ["/bin/bash" "/root/functions-start.sh"]
ENTRYPOINT ["/usr/bin/supervisord", "-c", "/etc/supervisor.d/supervisor.conf"]
