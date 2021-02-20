host=172.16.38.35

version=no_dw.v0.2.5.0

company_code=CSR1000083
# zlims-pro语言版本 中文：zh_CN  英文：en_US
language=zh_CN
# zlims-pro系统版本 填 ztron, lite
system_code=lite




record="${host}_${version}_${company_code}_${language}_${system_code}.txt"
rm -fr /var/jenkins_home/workspace/auto_deploy.done /var/jenkins_home/workspace/auto_deploy.sh /var/jenkins_home/workspace/auto_deploy.fail
count=0
echo "python3 auto_deploy.py ${host} 22 ${version} ${company_code} ${language} ${system_code}" > /var/jenkins_home/workspace/auto_deploy.sh
while [ "1" = "1" ]; do
	sleep 10;
    if [ -e /var/jenkins_home/workspace/auto_deploy.done ]; then
        rm /var/jenkins_home/workspace/auto_deploy.sh
        cat /var/jenkins_home/workspace/auto_deploy.log
        echo "${host} ${version} ${company_code} ${language} ${system_code}" > ${record}
    	break;
    fi
    if [ -e /var/jenkins_home/workspace/auto_deploy.fail ]; then
        rm /var/jenkins_home/workspace/auto_deploy.sh
        cat /var/jenkins_home/workspace/auto_deploy.log
        echo "部署失败"
    	exit 2;
    	break;
    fi
    # 6 是一分钟，2小时还没有部署成功即为部署超时
    if [ ${count} -ge 720 ]; then
        rm /var/jenkins_home/workspace/auto_deploy.sh
        cat /var/jenkins_home/workspace/auto_deploy.log
        echo "部署超时"
    	exit 2;
    fi
    count=`expr ${count} + 2`
    echo "wait for auto deploy..."
done