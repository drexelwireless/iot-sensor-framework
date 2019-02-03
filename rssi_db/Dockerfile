FROM ubuntu:16.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update

# Install mysql-5.7 & use the root password 'bellyband'.
RUN echo 'mysql-server mysql-server/root_password password bellyband' | debconf-set-selections
RUN echo 'mysql-server mysql-server/root_password_again password bellyband' | debconf-set-selections
RUN apt-get -y install mysql-server-5.7
RUN apt-get -y install libmysqlclient-dev

RUN apt-get -y install python2.7
RUN apt-get -y install python-pip
RUN apt-get -y install python-dev
RUN pip install --upgrade pip

RUN apt-get -y install libcurl4-openssl-dev
RUN apt-get -y install libffi-dev
RUN apt-get -y install libssl-dev
ENV PYCURL_SSL_LIBRARY=openssl

RUN pip install flask
RUN pip install MySQL-python
RUN pip install numpy
RUN pip install pycurl --global-option="--with-openssl"
RUN pip install pycrypto
RUN pip install python-dateutil

EXPOSE 3306
