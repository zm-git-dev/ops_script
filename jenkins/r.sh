cd /home/ztron/myGit/auto_deploy
status=`ps -ef | grep "python3 auto_deploy.py" | grep -v grep`
if [ "${status}" = "" ];then
if [ -e /home/jenkins_home/workspace/workspace/auto_deploy.sh ]; then
	sh /home/jenkins_home/workspace/workspace/auto_deploy.sh 1> /home/jenkins_home/workspace/workspace/auto_deploy.log 2>/home/jenkins_home/workspace/workspace/auto_deploy.log;
	if [ "$?" == "0" ]; then
	    echo "done" > /home/jenkins_home/workspace/workspace/auto_deploy.done;
	else
	    echo "fail" > /home/jenkins_home/workspace/workspace/auto_deploy.fail;
	fi
fi
else
    echo "is deploying, waiting it finish...."
fi
