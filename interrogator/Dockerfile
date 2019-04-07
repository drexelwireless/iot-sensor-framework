FROM ubuntu:16.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update

RUN apt-get -y install git

RUN apt-get -y install python2.7
RUN apt-get -y install python-pip
RUN apt-get -y install python-dev
RUN pip install --upgrade pip

RUN apt-get -y install mysql-server-5.7
RUN apt-get -y install libmysqlclient-dev

RUN pip3 install pymysql
RUN pip3 install httplib2
RUN pip3 install twisted
