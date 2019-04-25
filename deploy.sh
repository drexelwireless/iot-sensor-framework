#!/bin/bash

sudo apt-get update

sudo apt-get -y install python3.6
sudo apt-get -y install python-pip
sudo apt-get -y install python-dev
sudo apt-get -y install python3-dev
pip3 install --upgrade pip

sudo apt-get -y install mysql-server #-5.7
sudo apt-get -y install libmysqlclient-dev
sudo mysql_secure_installation
sudo mysqld --initialize #was mysql_install_db, may need to make an empty /var/lib/mysql directory and chown mysql:mysql with full permissions

sudo pip3 install pymysql
sudo pip3 install httplib2
sudo pip3 install twisted

# Install mysql-5.7 & use the root password 'bellyband'.
echo 'mysql-server mysql-server/root_password password bellyband' | debconf-set-selections
echo 'mysql-server mysql-server/root_password_again password bellyband' | debconf-set-selections

sudo apt-get -y install libcurl4-openssl-dev
sudo apt-get -y install libffi-dev
sudo apt-get -y install libssl-dev
export PYCURL_SSL_LIBRARY=openssl

sudo pip3 install flask
sudo pip3 install pymysql
sudo pip3 install numpy
sudo pip3 install pycurl --global-option="--with-openssl"
sudo pip3 install pycrypto
sudo pip3 install python-dateutil

# Packages needed by common ML/DSP systems that depend on the IOT Sensor Framework
sudo pip3 install pandas
sudo pip3 install filterpy
sudo pip3 install httplib2
sudo pip3 install werkzeug
sudo pip3 install hashlib
sudo pip3 install sklearn
sudo pip3 install pykalman
sudo pip3 install scikit-image
sudo pip3 install peakutils
sudo pip3 install hmmlearn
sudo pip3 install git+git://github.com/statsmodels/statsmodels

sudo apt-get install libmysqlclient-dev
sudo pip3 install MySQL-python
sudo pip3 install pycurl --global-option="--with-openssl"
sudo pip3 install pycrypto
sudo pip3 install python-dateutil
sudo pip3 install httplib2 # may need to manually remove and then upgrade to fix a bug in httplib2 regarding verifying SSL certificates
sudo pip3 install twisted
sudo pip3 install mysqlclient
sudo pip3 install pymysql
sudo pip3 install service_identity
sudo apt-get install python-matplotlib
sudo apt-get install libblas-dev liblapack-dev libatlas-base-dev gfortran
sudo pip3 install scipy

# for client packages
sudo pip3 install scikit-learn
sudo apt-get install libfreetype6-dev libpng3
sudo pip3 install --upgrade pip
sudo pip3 install --upgrade filterpy # this upgrades numpy / scipy stack

sudo pip3 install git+https://github.com/ajmendez/PyMix.git