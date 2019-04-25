FROM ubuntu:16.04
ENV DEBIAN_FRONTEND=noninteractive

RUN sudo apt-get update
RUN sudo apt-get -y install git

RUN ../deploy.sh

EXPOSE 3306
EXPOSE 5000
