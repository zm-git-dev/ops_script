host=172.16.38.54

version=no_dw.v0.2.5.0


record="${host}_${version}.txt"
rm -fr /var/jenkins_home/workspace/auto_update_deploy.done /var/jenkins_home/workspace/auto_update_deploy.sh /var/jenkins_home/workspace/auto_update_deploy.fail
count=0
echo "python3 auto_update_deploy.py ${host} 22 ${version}" > /var/jenkins_home/workspace/auto_update_deploy.sh
while [ "1" = "1" ]; do
    sleep 10;
    if [ -e /var/jenkins_home/workspace/auto_update_deploy.done ]; then
        rm /var/jenkins_home/workspace/auto_update_deploy.sh
        cat /var/jenkins_home/workspace/auto_update_deploy.log
        echo "${host} ${version} ${company_code} ${language} ${system_code}" > ${record}
        break;
    fi
    if [ -e /var/jenkins_home/workspace/auto_update_deploy.fail ]; then
        rm /var/jenkins_home/workspace/auto_update_deploy.sh
        cat /var/jenkins_home/workspace/auto_update_deploy.log
        echo "部署失败"
        exit 2;
        break;
    fi
    # 6 是一分钟，2小时还没有部署成功即为部署超时
    if [ ${count} -ge 5720 ]; then
        rm /var/jenkins_home/workspace/auto_update_deploy.sh
        cat /var/jenkins_home/workspace/auto_update_deploy.log
        echo "部署超时"
        exit 2;
    fi
    count=`expr ${count} + 2`
    echo "wait for auto update deploy..."
done