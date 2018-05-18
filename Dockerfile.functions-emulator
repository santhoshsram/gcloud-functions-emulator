FROM ubuntu:18.04
MAINTAINER Santhosh Sundararaman

RUN apt-get update
RUN apt-get -y install build-essential
RUN apt-get -y install libssl-dev
RUN apt-get -y install curl
RUN apt-get -y install vim
RUN apt-get -y install net-tools
RUN apt-get -y install nodejs npm
RUN npm install -g @google-cloud/functions-emulator

ADD config.json /root/.config/configstore/\@google-cloud/functions-emulator/config.json
ADD functions-start.sh /root

EXPOSE 8010/tcp
EXPOSE 8008/tcp

ENTRYPOINT /bin/bash /root/functions-start.sh
