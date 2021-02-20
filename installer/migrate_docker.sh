sudo mkdir -p /home/docker/lib
libpath=/var/lib/docker
#container_id=`sudo docker container ls| tail -1 | awk '{print $1}'`
#logpath=`sudo docker inspect ${container_id} | grep HostnamePath | awk '{print $2}' | sed -e 's/[",]//g'`
#libpath=dirname `dirname `dirname $logpath``
sudo cp -fr $libpath /home/docker/lib
sudo systemctl stop docker
sudo sed -i 's#ExecStart=.\+#ExecStart=/usr/bin/dockerd --graph=/home/docker/lib/docker#' /usr/lib/systemd/system/docker.service
sudo systemctl daemon-reload
sudo systemctl start docker
sudo rm -fr /var/lib/docker
