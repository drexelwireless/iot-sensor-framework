#!/bin/bash

sudo apt-get update

sudo apt-get -y install python3.6
sudo apt-get -y install python-pip
sudo apt-get -y install python3-pip
sudo apt-get -y install python-dev
sudo apt-get -y install python3-dev
pip3 install --upgrade pip

sudo apt-get -y install mysql-server #-5.7
sudo apt-get -y install libmysqlclient-dev
sudo mysql_secure_installation
sudo mysqld --initialize #was mysql_install_db, may need to make an empty /var/lib/mysql directory and chown mysql:mysql with full permissions

pip3 --user install twisted

# Install mysql-5.7 & use the root password 'bellyband'.
echo 'mysql-server mysql-server/root_password password bellyband' | debconf-set-selections
echo 'mysql-server mysql-server/root_password_again password bellyband' | debconf-set-selections

sudo apt-get -y install libcurl4-openssl-dev
sudo apt-get -y install libffi-dev
sudo apt-get -y install libssl-dev
export PYCURL_SSL_LIBRARY=openssl

pip3 --user install flask
pip3 --user install numpy
pip3 --user install python-dateutil

# Packages needed by common ML/DSP systems that depend on the IOT Sensor Framework
pip3 --user install pandas
pip3 --user install filterpy
pip3 --user install werkzeug
#pip3 --user install hashlib
pip3 --user install sklearn
pip3 --user install pykalman
pip3 --user install scikit-image
pip3 --user install peakutils
pip3 --user install hmmlearn
pip3 --user install statsmodels 

sudo apt-get install libmysqlclient-dev
#pip3 --user install MySQL-python # may be incompatible with Python3, switch to pymysql instead.
pip3 --user install pycurl --global-option="--with-openssl"
pip3 --user install pycrypto

#httplib2 default installation is incompatible with Python 3 when using SSL
PKGDIRS=`python -c "import site; p=site.getsitepackages(); print('\n'.join(str(x) for x in p))"`
for P in PKGDIRS
do
	find $P -iname '*httplib2*' -exec sudo mv {} /tmp
done
pip3 --user install httplib2 # may need to manually remove and then upgrade to fix a bug in httplib2 regarding verifying SSL certificates

pip3 --user install mysqlclient
pip3 --user install pymysql
pip3 --user install service_identity
sudo apt-get install python-matplotlib
sudo apt-get install libblas-dev liblapack-dev libatlas-base-dev gfortran
pip3 --user install scipy
pip3 --user install sllurp
pip3 --user install tinymongo

# for client packages
pip3 --user install scikit-learn
sudo apt-get install libfreetype6-dev libpng3
pip3 --user install --upgrade pip
pip3 --user install --upgrade filterpy # this upgrades numpy / scipy stack

sudo apt-get install libgsl0-dev
sudo apt-get install libgsl0ldbl

#sudo pip install git+https://github.com/ajmendez/PyMix.git
git clone https://github.com/ajmendez/PyMix.git
touch PyMix/README.rst
sed 's/from distutils.core import setup, Extension,DistutilsExecError/#from distutils.core import setup, Extension,DistutilsExecError\nfrom distutils.core import setup, Extension' PyMix/setup.py
python3 PyMix/setup.py install
