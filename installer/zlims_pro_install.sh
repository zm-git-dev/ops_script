sudo docker load -i nlims_pg.tar

if [ "$1" = "no" ]; then
    :
else
    volume_name=pgdata_pro

    sudo docker volume create ${volume_name}
    volume_path=`sudo docker volume inspect ${volume_name}  | grep Mountpoint | awk '{print \$2}' | sed -e 's/[",]//g'`
    sudo cp -rf _data/* ${volume_path}
fi


cp nlims.sh nlims_auto.sh

cp nlims.service nlims_auto.service

cp nlims_ftp.service nlims_ftp_auto.service

cp backup_mark.sh backup_auto.sh

cp ftp.sh start_ftp.sh

CURRENT_PATH=$(cd "$(dirname "$0")"; pwd)
echo $CURRENT_PATH
CURRENT_MESSAGE=en_US
sed -i "s!start_url!$CURRENT_PATH!g" nlims_auto.sh

sed -i "s!start_url!$CURRENT_PATH!g" nlims_auto.service

sed -i "s!start_url!$CURRENT_PATH!g" nlims_ftp_auto.service

sed -i "s!start_url!$CURRENT_PATH!g" backup_auto.sh

sed -i "s!start_url!$CURRENT_PATH!g" start_ftp.sh

sed -i "s!start_url!$CURRENT_PATH!g"  zsm/tomcat/bin/setclasspath.sh

sed -i "s!zh_CN!${CURRENT_MESSAGE}!g" nlims/config/application-pro.properties

sed -i "s!start_url!$CURRENT_PATH!g" nlims/config/application-pro.properties

chmod 700 start_ftp.sh

chmod 700 nlims_auto.sh

chmod 700 backup_auto.sh

sudo cp nlims_auto.service /etc/systemd/system/nlims_auto.service 

sudo cp nlims_ftp_auto.service /etc/systemd/system/nlims_ftp_auto.service

if sudo grep "backup_auto.sh" /etc/crontab -n
then
   echo 'backup is exists';
else
    echo 'backup not exists';
    sudo cat /etc/crontab > ./crontab
    echo "0 23 * * * root $CURRENT_PATH/backup_auto.sh" >> ./crontab
    sudo cp ./crontab /etc/crontab
fi

sudo systemctl daemon-reload

sudo systemctl restart crond.service 2>/dev/null
sudo systemctl restart cron.service 2>/dev/null


sudo systemctl enable nlims_auto.service

sudo systemctl enable nlims_ftp_auto.service

