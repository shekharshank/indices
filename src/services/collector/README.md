INDICES Performance Data Collector

On Collectd server:
=====

Download Indices:
===

```
mkdir $HOME/indices
cd $HOME/indices
git clone https://github.com/shekharshank/indices.git
```

Install GO:
====

https://tecadmin.net/install-go-on-ubuntu/

```
mkdir /home/ubuntu/golang
cd /home/ubuntu/golang
wget https://storage.googleapis.com/golang/go1.8.linux-amd64.tar.gz
sudo tar -xvf *
sudo mv go /usr/local


echo 'export GOROOT=/usr/local/go' >> ~/.bashrc
echo 'export GOPATH=$HOME/indices/indices/src/services/collector' >> ~/.bashrc
echo 'export PATH=$PATH:$GOROOT/bin:$GOPATH/bin' >> ~/.bashrc
echo 'export GOBIN=$GOPATH/bin' >> ~/.bashrc
source ~/.bashrc
cd $HOME/indices/indices/src/services/collector
go get

```



Install Influxdb:
====

http://www.andremiller.net/content/grafana-and-influxdb-quickstart-on-ubuntu


```
curl -sL https://repos.influxdata.com/influxdb.key | sudo apt-key add -
source /etc/lsb-release
echo "deb https://repos.influxdata.com/${DISTRIB_ID,,} ${DISTRIB_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/influxdb.list
```


```
sudo apt-get update && sudo apt-get install influxdb
```

Start the service
```
sudo service influxdb start
```


Install NTP
===

install ntpdate & ntp


```
sudo apt-get install ntpdate

ntpdate 0.ro.pool.ntp.org

sudo apt-get install ntp
sudo service ntpd start
```


Install RabbitMQ Server:


```

echo 'deb http://www.rabbitmq.com/debian/ testing main' |
        sudo tee /etc/apt/sources.list.d/rabbitmq.list

wget -O- https://www.rabbitmq.com/rabbitmq-release-signing-key.asc |
        sudo apt-key add -

sudo apt-get update


sudo apt-get install rabbitmq-server
```

In the Collector.go program set following:

Set 

```
<user> eg: indices_user
<pass> eg: indices_manager
<collectd-queue> eg: collectd-queue
<collectd-key> eg: collectd-key
```
Also add the following user/password in the RabbitMQ

``
 sudo rabbitmqctl add_user <user> <pass>
 sudo rabbitmqctl  set_permissions -p / <user> ".*" ".*" ".*"

``

Misc. commands for deleting the queue

```
  sudo rabbitmqctl purge_queue "indices_queue"
```

Enable the custom TCP port access to the Collector.go server for
Port Number for 5672.

Misc. Commands for Influxdb
```
Create Influx-db
SHOW DATABASES
drop database "collectd-db"
create database "collectd-db"
use collectd-db
show series
show * from host_metrics

```
