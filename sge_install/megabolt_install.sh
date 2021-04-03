user=`whoami`
if  [ "${user}" != "root" ]; then
    echo "Error: you must run as root."
    exit 2
fi
rm -fr /opt/sysoft/sge/*
python installer.py stopsge
python installer.py setup
python installer.py installmaster MegaBOLT_Workstation 192.168.122.1
source ~/.bashrc
python installer.py addqueue mb.q @mb MegaBOLT_Workstation
python installer.py startsge
sleep 2
source ~/.bashrc
python installer.py stopsge
python installer.py startsge
echo "================================================================"
echo 'Your system environment update, Please execute: source ~/.bashrc'
echo 'We recommend to migrate docker path to /home, you can execute the command to migrate docker: sh /home/ztron/app_software/wdl_script/migrate_docker.sh'
echo "================================================================"
