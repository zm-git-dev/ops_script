#!/usr/bin/python

import os
import socket
from config import SHARE_DATA_PATH, RSYNC_PATH, DATA_WARE_HOUSE
import sys
import getopt
import json
import re
import time
import subprocess
import getpass
from sys import version_info


'''
    auto answer key:
    INIT_ZLIMS_PRO_DB
    REMOVE_OLD_FILE_MANAGE
    DW_PATH
    INIT_PAAZ_DB
    ZLIMS_PRO_COMPANY_CODE
    ZLIMS_PRO_LANGUAGE
    ZLIMS_PRO_SYSTEM_VERSION
    INSTALL_PYTHON3
'''

def get_zlims_pro_database_path():
    volume_name = 'pgdata_pro'
    cmd = "sudo docker volume inspect %s  | grep Mountpoint | awk '{print $2}' | sed -e 's/[\",]//g'" % volume_name
    try:
        fh = os.popen(cmd, 'r')
        path = fh.read().strip()
        fh.close()
    except:
        print("Warning: can not get zlims pro volume path")
        path = "/var/lib/docker/volumes/pgdata_pro/_data"
    return path

app_software_path = os.path.realpath(sys.path[0]) #os.path.join(os.path.realpath(sys.path[0]), 'app_software')
ztron_store = os.path.join(SHARE_DATA_PATH, "ztron")
data_ware_house = os.path.join(DATA_WARE_HOUSE, "ztron")
config_install_path = '/home/ztron/.config'
sdk_image_name = "zlims-db:zlims-dist_0.1.0.0"
sdk_path = os.path.join(app_software_path, 'mgi-zlims-image-*')
START = 'start'
RESTART = 'restart'
STOP = 'stop'
STATUS = 'status'
INSTALL = 'install'
SETUP = 'setup'
LOG = 'log'
TEST = 'test'
UPDATE_DW = "updatedw"
UPDATE_SD = "updatesd"
CONFIG = "config"
CLEARUP = "clearup"
MIGRATE = "migrate"
environment = "export PATH=/opt/sysoft/pgsql/bin:$PATH; export PGDATA=/opt/sysoft/pgsql/data;export PGUSER=ztron;export PGPORT=54321;"
auto_answer_json = {}

def check_and_install_python3():
    cmd = "which python3 2>/dev/null"
    fh = os.popen(cmd, 'r')
    context = fh.read()
    fh.close()
    if context:
        print("python3 install path: %s" % context)
    else:
        answer = get_answer("python3 is not in your system, do you want to install python3?(default: yes)", "INSTALL_PYTHON3")
        if answer in ['n', 'N', 'no', 'No']:
            print("Warmming canceled install python3.")
        else:
            cmd = "cd %s/wdl_script; sh dependence_install.sh offline python" % app_software_path
            exec_system_cmd(cmd)
    cmd = "cd %s/wdl_script; sh dependence_install.sh offline pip" % app_software_path
    exec_system_cmd(cmd)
            

def clearup():
    # answer = get_answer("Do you want to clear up system data(yes or no ? default:yes):")
    # if answer in ['y', 'Y', 'yes', 'Yes']:
    print("Cromwell Start to clean up...")
    cromwell_clearup_cmd = os.path.join(app_software_path, 'cromwell48', 'clearup.sh')
    exec_system_cmd(cromwell_clearup_cmd)
    print("Cromwell Clean up done.")

    print("Bp_auto Start to clean up...")
    execute_sql_sh = os.path.join(app_software_path, 'wdl_script', "execute_sql.sh")
    bp_auto_clearup_cmd = "sh %s %s" % (execute_sql_sh, os.path.join(app_software_path, "clearup", "paaz_clear.sql"))
    exec_system_cmd(bp_auto_clearup_cmd)
    print("Bp_auto Clean up done.")

    print("Zlims-pro Start to clean up...")
    clearup_cmd = "cd %s/zlims-pro/nlims/clear-sample ; sudo sh clear_sample.sh" % app_software_path
    exec_system_cmd(clearup_cmd)
    print("Zlims-pro Clean up done.")


def migration():
    print("Start to migrate...")
    migration_folder = os.path.join(app_software_path, "migration")
    cmd = "cd %s; sh %s/migration.sh" % (migration_folder, migration_folder)
    exec_system_cmd(cmd)
    print("Migrate done.")


def replace_system_logo(version):
    print("Changing system manager logo......")
    logo_mapping = {
        "lite": "false",
        "ztron": "true"
    }
    cmds = [
        "cd /home/ztron/app_software/system_manage",
        "rm -fr .build 2>/dev/null",
        "mkdir -p .build",
        "cd .build",
        "unzip /home/ztron/app_software/system_manage/system-manage.jar 1>/dev/null && rm /home/ztron/app_software/system_manage/system-manage.jar",
        "sed -i 's/ztron:.\+/ztron: %s/' BOOT-INF/classes/application-prod.yml" % logo_mapping.get(version, "true"),
        "jar -cvfM0 /home/ztron/app_software/system_manage/system-manage.jar ./ 1>/dev/null && cd .. && rm -fr .build 2>/dev/null",
    ]
    status = exec_system_cmd("\n".join(cmds))
    if status == 0:
        service_manager(apps_detail.get("common_system_manage", {}).get("service_name"), "restart")
        print("Change system manager logo......done")
    else:
        print("Changing system manager logo......failed")

    logo_mapping = {
        "lite": "true",
        "ztron": "false"
    }
    cmds = [ "sed -i 's/global.CONFIG_SHOW_ZLIMS_LOGO.\+/global.CONFIG_SHOW_ZLIMS_LOGO = %s/' /home/ztron/app_software/appMarketClient/web/utils/config.js" % logo_mapping.get(version, "false"),
             "sed -i 's/global.CONFIG_SHOW_ZLIMS_LOGO.\+/global.CONFIG_SHOW_ZLIMS_LOGO = %s/' /home/ztron/app_software/biopass_web/config/config.js" % logo_mapping.get(version, "false"),
             "sed -i 's/global.CONFIG_SHOW_ZLIMS_LOGO.\+/global.CONFIG_SHOW_ZLIMS_LOGO = %s/' /home/ztron/app_software/system_update/web/utils/config.js" % logo_mapping.get(
                 version, "false"),
             ]
    status = exec_system_cmd("\n".join(cmds))
    if status == 0:
        service_manager(apps_detail.get("common_system_manage", {}).get("service_name"), "restart")
        service_manager(apps_detail.get("biopass_web", {}).get("service_name"), "restart")
        service_manager(apps_detail.get("app_client_web", {}).get("service_name"), "restart")
        service_manager("ztronSystemUpdateWeb.service", "restart")
        print("Change bp_auto, market logo......done")
    else:
        print("Changing bp_auto, market logo......failed")

def config_zlims_pro():
    config_path = os.path.join(app_software_path, 'zlims-pro', 'nlims', 'config', 'application-pro.properties')
    answer = get_answer("Please input new company code to update:", "ZLIMS_PRO_COMPANY_CODE")
    if answer:
        replace_config("ztron-company-num", answer, config_path)
        change_company_code_sql = """update bp_auto.t_app_order set enterprise_code = '%(company_code)s';update bp_auto.t_dl_user set companynum = '%(company_code)s';update bp_auto.sys_user_workflow set companynum = '%(company_code)s';""" % {
            "company_code": answer
        }
        execute_sql_sh = os.path.join(app_software_path, 'wdl_script', "execute_sql.sh")
        cmd = "echo \"%s\" > .temp.sql; sh %s .temp.sql" %(change_company_code_sql, execute_sql_sh)
        exec_system_cmd(cmd)
        print("Company code: success.")
    else:
        print("Nothing to update.")

    answer = get_answer("Please input new system language to update(zh_CN/en_US):", "ZLIMS_PRO_LANGUAGE")
    if answer and answer in ['zh_CN', 'en_US']:
        replace_config("basic-locale", answer, config_path)
        print("System language update: success.")
    else:
        print("Input error, Nothing to update.")

    answer = get_answer("Please input system version to update(lite/ztron):", "ZLIMS_PRO_SYSTEM_VERSION")
    if answer and answer in ['lite', 'ztron']:
        replace_system_logo(answer)
        keys = ['sys.login-url', 'sys.index-page', 'ztron']
        values = ['login-ztron', 'index-ztron', 'true'] if answer == 'ztron' else ['login', 'index', 'paaz']
        for k, v in zip(keys, values):
            replace_config(k, v, config_path)
        print("System version update: success.")
    else:
        print("Input error, Nothing to update.")
    print("Restart zlims-pro")
    service_manager("nlims_auto.service", "restart")
    backup_zlims_pro_config()


def fix_java_home():
    cmd = "sudo ls ${JAVA_HOME}/jre/bin/java 2>/dev/null"
    fh = os.popen(cmd, 'r')
    context = fh.read()
    fh.close()
    jar_files = ["cldrdata.jar", "dnsns.jar", "jaccess.jar", "localedata.jar", "nashorn.jar", "sunec.jar", "sunjce_provider.jar", "sunpkcs11.jar", "zipfs.jar"]
    if not context and os.environ.get("JAVA_HOME"):
        cmd = "sudo mkdir -p ${JAVA_HOME}/jre/bin; sudo ln -s `which java` ${JAVA_HOME}/jre/bin/"
        exec_system_cmd(cmd)
        java_home = os.path.join(os.environ.get("JAVA_HOME"), "jre", "bin")
        java = os.path.join(java_home, "java")
        if not os.path.exists(java):
            cmd = "sudo mkdir -p ${JAVA_HOME}/jre/bin; sudo ln -s `which java` ${JAVA_HOME}/jre/bin/"
            exec_system_cmd(cmd)
    if os.environ.get("JAVA_HOME"):
        java_home = os.path.join(os.environ.get("JAVA_HOME"), "jre", "lib", "ext")
        if not os.path.exists(java_home):
            cmd = "sudo mkdir -p %s" % java_home
            exec_system_cmd(cmd)
        for jar in jar_files:
            target_path = os.path.join(java_home, jar)
            if not os.path.exists(target_path):
                cmd = "sudo cp %s %s" % (os.path.join(app_software_path, "java_source", jar), target_path)
                exec_system_cmd(cmd)


def open_system_port(port):
    cmd = "systemctl status firewalld.service | grep \"active (running)\" | grep -v grep"
    fh = os.popen(cmd, 'r')
    if fh.read():
        cmd = "sudo iptables -I INPUT -p tcp --dport %s -j ACCEPT; sudo firewall-cmd --zone=public --add-port=%s/tcp --permanent 1>/dev/null 2>/dev/null" % (port, port)
        exec_system_cmd(cmd)
    fh.close()


def exec_system_cmd(cmd):
    status = os.system(cmd)
    if status != 0:
        print("Warning: exec %s, return code: %s" % (cmd, status))
    return status


def replace_config(key, target_str, config_file):
    cmd = "sed -i 's|%s \\?= \\?.\\+|%s=%s|' %s" % (key, key, target_str, config_file)
    exec_system_cmd(cmd)


def get_value_from_config(key, config_file):
    cmd = "cat %s | grep %s | awk -F'=' '{print $2}'" % (config_file, key)
    fh = os.popen(cmd)
    value = fh.read().strip()
    print("Get last config key: %s, value: %s" % (key, value))
    return value


def stop_rsync():
    cmd = "sudo systemctl stop rsyncd"
    exec_system_cmd(cmd)


def start_rsync():
    cmd = "sudo systemctl start rsyncd"
    exec_system_cmd(cmd)


def install_service(service, install_path=None):
    service_name = os.path.basename(service)
    cmd = 'sudo cp %s /etc/systemd/system; ' % service
    if install_path:
        cmd += "sudo sed -i 's|__INSTALL_PATH__|%s|g' %s;" % (install_path, os.path.join('/etc/systemd/system', service_name))
    cmd += 'sudo systemctl enable %s; sudo systemctl daemon-reload' % service_name
    exec_system_cmd(cmd)


def service_manager(service, command, no_output=False):
    cmd = "sudo systemctl %s %s" % (command, service)
    if command == STATUS:
        cmd = "systemctl --no-pager status %s" % service
    if no_output:
        cmd = "nohup %s 1>/dev/null 2>/dev/null" % cmd
    return exec_system_cmd(cmd)


def install_rsync():
    cmd = 'sudo mkdir -p %s; sudo chown -R ztron:ztron %s' % (RSYNC_PATH, RSYNC_PATH)
    exec_system_cmd(cmd)
    software_path = os.path.join(app_software_path, 'rsync')
    config_path = os.path.join(software_path, 'installer.conf')
    replace_config('rsync_path', RSYNC_PATH, config_path)
    update_config_to_table('rsyncPath', RSYNC_PATH)
    cmd = 'cd %s; sh installer.sh' % software_path
    exec_system_cmd(cmd)


def creat_log_folder():
    cmd = "mkdir -p /home/ztron/logs; cd /home/ztron/logs; mkdir -p app-market-client file-manage system-manage  system-update"
    exec_system_cmd(cmd)


def install_ganglia():
    cmd = "sh /home/ztron/app_software/system_manage/installGanglia/installGanglia.sh"
    exec_system_cmd(cmd)


def install_docker():
    cmd = "cd %s; python installer.py --install-docker" % sdk_path
    exec_system_cmd(cmd)


def install_postgre_software():
    pg_tar = os.path.join(app_software_path, 'postgresql', 'pginit1.0.tar.gz')
    pg_install_path = "/opt/sysoft/pgsql"
    flag = True
    cmd = "sudo mkdir -p /opt/sysoft; sudo chown -R ztron:ztron /opt/sysoft"
    exec_system_cmd(cmd)
    print("Unzip postgre package, please wait......")
    cmd = "tar -zxvf %s 1>/dev/null" % pg_tar
    exec_system_cmd(cmd)
    print("Unzip...................................done")
    if os.path.exists(pg_install_path):
        answer = get_answer("Pgsql have exists, do you want remove and install init database?(default: no)", "INIT_PAAZ_DB")
        if answer in ['y', 'Y', 'yes', 'Yes']:
            cmd = "sudo mv %s /opt/sysoft/pgsql_backup" % pg_install_path
            exec_system_cmd(cmd)
        else:
            flag = False
    if flag:
        cmd = "sudo mv pgsql_init %s; sudo chown -R ztron:ztron %s" % (pg_install_path, pg_install_path)
        exec_system_cmd(cmd)
        env = '''
    export PATH=/opt/sysoft/pgsql/bin:$PATH
    export PGDATA=/opt/sysoft/pgsql/data
    export PGUSER=ztron
    export PGPORT=54321
    '''
        cmd = "sed -i 's/port = 5432\\s/port = 54321/' /opt/sysoft/pgsql/data/postgresql.conf"
        exec_system_cmd(cmd)
        with open('/home/ztron/.bashrc', 'a') as fh:
            fh.write(env)


def install_postgre():
#    if not os.path.exists('/opt/sysoft/pgsql/bin/psql'):
#        install_postgre_software()
    software_path = os.path.join(app_software_path, 'postgresql')
    cmd = 'cd %s; sh installer.sh' % software_path
    exec_system_cmd(cmd)


def install_cromwell():
    cromwell_work_path = os.path.join(ztron_store, "analysis")
    cmd = 'sudo mkdir -p %s; sudo chown -R ztron:ztron %s' % (cromwell_work_path, cromwell_work_path)
    exec_system_cmd(cmd)
    software_path = os.path.join(app_software_path, 'cromwell48')
    config_path = os.path.join(software_path, 'config.txt')
    replace_config('second_analysis_path', cromwell_work_path, config_path)
    cmd = 'cd %s; sh installer.sh' % software_path
    exec_system_cmd(cmd)


def install_app_client_server():
    service = os.path.join(app_software_path, 'service', apps_detail.get("app_client_service", {}).get("service_name"))
    install_service(service)


def install_app_client_web():
    service = os.path.join(app_software_path, 'service', apps_detail.get("app_client_web", {}).get("service_name"))
    install_service(service)


def install_common_system_manage():
    service = os.path.join(app_software_path, 'service', apps_detail.get("common_system_manage", {}).get("service_name"))
    install_service(service)


def update_config_to_table(key, value):
    sql = "UPDATE bp_auto.t_dl_config SET c_value='%s' WHERE c_key='%s'" % (value, key)
    execute_sh = os.path.join(app_software_path, "wdl_script", "execute_sql.sh")
    sql_file = '.temp.sql'
    with open(sql_file, 'w') as fh:
        fh.write(sql)
        cmd = "%s\nsh %s %s" % (environment, execute_sh, sql_file)
    exec_system_cmd(cmd)


def get_config_value(key):
    sql = "select c_value from bp_auto.t_dl_config WHERE c_key='%s'" % key
    execute_sh = os.path.join(app_software_path, "wdl_script", "execute_sql.sh")
    sql_file = '.temp.sql'
    with open(sql_file, 'w') as fh:
        fh.write(sql)
        cmd = "%s\nsh %s %s | tail -3 | head -1" % (environment, execute_sh, sql_file)
    fh = os.popen(cmd, 'r')
    return fh.read()


def update_sd():
    origin_sd_path = get_config_value("autorunDW")
    origin_sd_path = "/" + origin_sd_path.strip().split("/")[1]
    while True:
        msg = "Currently SD path is: %s\n======= Important: data warehouse path ztron account must exists" \
              "=======\nWhere path do you want change to:" % origin_sd_path
        answer = get_answer(msg, "SD_PATH")
        if os.path.exists(answer):
            ztron_path = os.path.join(answer, "ztron")
            autorunDW = os.path.join(ztron_path, "autorunDW")
            cromwell_work_path = os.path.join(ztron_path, "analysis")
            cmd = 'sudo mkdir -p %s; sudo chown -R ztron:ztron %s' % (cromwell_work_path, cromwell_work_path)
            exec_system_cmd(cmd)
            cmd = 'sudo mkdir -p %s; sudo chown -R ztron:ztron %s' % (autorunDW, autorunDW)
            exec_system_cmd(cmd)
            software_path = os.path.join(app_software_path, 'cromwell48')
            config_path = os.path.join(software_path, 'config.txt')
            replace_config('second_analysis_path', cromwell_work_path, config_path)
            cmd = 'cd %s; sh installer.sh' % software_path
            exec_system_cmd(cmd)
            update_config_to_table('autorunDW', autorunDW)
            service_manager(apps_detail.get("cromwell", {}).get("service_name"), "restart")
            service_manager(apps_detail.get("bp_auto", {}).get("service_name"), "restart")
            print("SD path changed to %s.\n" % answer)
            break
        else:
            print("Error: input path %s, is not exists, please input again, or ctrl + c to exit." % answer)


def update_wd():
    origin_wd_path = get_config_value("autoStore_unStandardWarehouseRootDir")
    origin_wd_path = origin_wd_path.strip()
    while True:
        msg = "Currently WarehouseRootDir path is: %s\n======= Important: data warehouse path ztron account must have write" \
              " permission=======\nWhere path do you want change to:" % origin_wd_path
        answer = get_answer(msg, "DW_PATH")
        if os.path.exists(answer):
            # rootDir = os.path.join(answer, "ztron_auto_store_dev")
            # cmd = "sudo mkdir -p %s; chown -R ztron:ztron %s" % (rootDir, rootDir)
            # exec_system_cmd(cmd)
            # autoStore_standardWarehouseRootDir = os.path.join(rootDir, "standardWarehouse")
            # update_config_to_table('autoStore_standardWarehouseRootDir', autoStore_standardWarehouseRootDir)
            # autoStore_unStandardWarehouseRootDir = os.path.join(rootDir, "unStandardWarehouse")
            if not answer.endswith("/"):
                answer = answer + "/"
            autoStore_unStandardWarehouseRootDir = answer
            update_config_to_table('autoStore_unStandardWarehouseRootDir', autoStore_unStandardWarehouseRootDir)
            update_config_to_table('store_nonstandard_root_path', autoStore_unStandardWarehouseRootDir)
            print("WarehouseRootDir changed to %s.\nPlease make sure this path ztron have write permission." % answer)
            break
        else:
            print("Error: input path %s, is not exists, please input again, or ctrl + c to exit." % answer)


def install_file_manage():
    software_3part = os.path.join(app_software_path, 'file_manage', 'init_data')
    software_3part_install_path = data_ware_house
    if os.path.exists(os.path.join(software_3part_install_path, "standardWarehouse")):
        msg = "File manage path: %s have exist,\nDo you wants remove old install?(yes/no default: no)" % software_3part_install_path
        answer = get_answer(msg, "REMOVE_OLD_FILE_MANAGE")
        if answer in ['y', 'Y', 'yes', 'Yes']:
            cmd = 'cd %s;rm -fr autoStore/ bigdata_dw/ seqArcPython ztron_auto_store_dev/ ztron_storage_manage_dev/  bam2cramTmpFile/ ref/ StdTest/ ztron-file2file.jar' % software_3part_install_path
            exec_system_cmd(cmd)
            create_folder(software_3part_install_path)
            cmd = 'cp -fr %s/* %s;' % (software_3part, software_3part_install_path)
            exec_system_cmd(cmd)
    else:
        create_folder(software_3part_install_path)
        cmd = 'cp -fr %s/* %s;' % (software_3part, software_3part_install_path)
        exec_system_cmd(cmd)

    autoStore_standardWarehouseRootDir = "%s/ztron_auto_store_dev/standardWarehouse/" % software_3part_install_path
    update_config_to_table('autoStore_standardWarehouseRootDir', autoStore_standardWarehouseRootDir)
    autoStore_unStandardWarehouseRootDir = "%s/ztron_auto_store_dev/unStandardWarehouse/" % software_3part_install_path
    update_config_to_table('autoStore_unStandardWarehouseRootDir', autoStore_unStandardWarehouseRootDir)
    # bp_auto data ware house path
    update_config_to_table('store_nonstandard_root_path', autoStore_unStandardWarehouseRootDir)
    autoStore_copyFileJobScript = "%s/ztron_auto_store_dev/file2fileJob" % software_3part_install_path
    update_config_to_table('autoStore_copyFileJobScript', autoStore_copyFileJobScript)
    autoStore_copyFileJobOutputDir = "%s/ztron_auto_store_dev/sgeLog" % software_3part_install_path
    update_config_to_table('autoStore_copyFileJobOutputDir', autoStore_copyFileJobOutputDir)
    fileSystem_copyFileRootDir = "%s/ztron_storage_manage_dev/copy_file" % software_3part_install_path
    update_config_to_table('fileSystem_copyFileRootDir', fileSystem_copyFileRootDir)
    fileSystem_copyFileJobScript = "%s/ztron_storage_manage_dev/file2fileJob" % software_3part_install_path
    update_config_to_table('fileSystem_copyFileJobScript', fileSystem_copyFileJobScript)
    fileSystem_copyFileJobOutputDir = "%s/ztron_storage_manage_dev/sgeLog" % software_3part_install_path
    update_config_to_table('fileSystem_copyFileJobOutputDir', fileSystem_copyFileJobOutputDir)
    fileSystem_trashDir = "%s/ztron_storage_manage_dev/trash" % software_3part_install_path
    update_config_to_table('fileSystem_trashDir', fileSystem_trashDir)
    file2file_fileLockBaseDir = "%s/autoStore/auto_store_locks" % software_3part_install_path
    update_config_to_table('file2file_fileLockBaseDir', file2file_fileLockBaseDir)
    file2file_samtoolsLocation = "%s/samtools-1.9/bin/bin/samtools" % software_3part_install_path
    update_config_to_table('file2file_samtoolsLocation', file2file_samtoolsLocation)
    file2file_bamFastaBaseDir = "%s/bigdata_dw/utils/fasta4bam" % software_3part_install_path
    update_config_to_table('file2file_bamFastaBaseDir', file2file_bamFastaBaseDir)
    file2file_bam2cramTmpDir = "%s/bam2cramTmpFile" % software_3part_install_path
    update_config_to_table('file2file_bam2cramTmpDir', file2file_bam2cramTmpDir)
    file2file_seqArcLocation = "%s/StdTest/SeqArc" % software_3part_install_path
    update_config_to_table('file2file_seqArcLocation', file2file_seqArcLocation)
    file2file_seqArcPythonLocation = "%s/seqArcPython/comp_noidx.py" % software_3part_install_path
    update_config_to_table('file2file_seqArcPythonLocation', file2file_seqArcPythonLocation)
    file2file_seqArcDefaultRef = "%s/ref/hg19.fasta" % software_3part_install_path
    update_config_to_table('file2file_seqArcDefaultRef', file2file_seqArcDefaultRef)

    autoStore_file2fileJar = "%s/ztron-file2file.jar" % software_3part_install_path
    update_config_to_table('autoStore_file2fileJar', autoStore_file2fileJar)
    service = os.path.join(app_software_path, 'service', apps_detail.get("file_manage", {}).get("service_name"))
    install_service(service)


def install_monitor_manage():
    service = os.path.join(app_software_path, 'service', apps_detail.get("monitor_manage", {}).get("service_name"))
    cmd = "df -h %s | tail -1 | awk '{print $6}'" % SHARE_DATA_PATH
    try:
        fh = os.popen(cmd, 'r')
        root_path = fh.read().strip()
        fh.close()
    except:
        root_path = SHARE_DATA_PATH
    sql = "UPDATE bp_auto.t_system_storage_conf SET name='%s'" % root_path
    execute_sh = os.path.join(app_software_path, "wdl_script", "execute_sql.sh")
    sql_file = '.temp.sql'
    with open(sql_file, 'w') as fh:
        fh.write(sql)
        cmd = "%s\nsh %s %s" % (environment, execute_sh, sql_file)
    exec_system_cmd(cmd)
    install_service(service)


def install_system_update():
    service = os.path.join(app_software_path, 'system_update', 'server', 'ztronSystemUpdate.service')
    install_service(service, os.path.join(app_software_path, 'system_update', 'server'))
    service = os.path.join(app_software_path, 'system_update', 'web', 'ztronSystemUpdateWeb.service')
    install_service(service, os.path.join(app_software_path, 'system_update', 'web'))


def install_zlims_sdk():
    cmd = "cd %s; python installer.py --up" % sdk_path
    exec_system_cmd(cmd)


def install_zlims_pro():
    zlims_pro_database_path = get_zlims_pro_database_path()
    pro_path = os.path.join(app_software_path, 'zlims-pro')
    cmd = "sudo ls %s 2>/dev/null" % zlims_pro_database_path
    fh = os.popen(cmd, 'r')
    context = fh.read()
    fh.close()
    cmd = "cd %s; sh zlims_pro_install.sh" % pro_path
    if zlims_pro_database_path and context:
        msg = "ZLIMS Pro database have exists, do you want init it DB?(default:no)"
        answer = get_answer(msg, "INIT_ZLIMS_PRO_DB")
        if answer in ['y', 'Y', 'yes', 'Yes']:
            pass
        else:
            cmd += " no"
    exec_system_cmd(cmd)


def backup_zlims_pro_config():
    pro_path = os.path.join(app_software_path, 'zlims-pro')
    config_path = os.path.join(pro_path, 'nlims', 'config', 'application-pro.properties')
    cmd = "mkdir -p %s ; cp %s %s" % (config_install_path, config_path, config_install_path)
    exec_system_cmd(cmd)


def recover_config():
    pro_path = os.path.join(app_software_path, 'zlims-pro')
    config_path = os.path.join(pro_path, 'nlims', 'config', 'application-pro.properties')
    backup_config = os.path.join(config_install_path, 'application-pro.properties')
    answer = get_value_from_config("ztron-company-num", backup_config)
    replace_config("ztron-company-num", answer, config_path)
    answer = get_value_from_config("basic-locale", backup_config)
    replace_config("basic-locale", answer, config_path)
    answer = get_value_from_config("sys.login-url", backup_config)
    keys = ['sys.login-url', 'sys.index-page', 'ztron']
    values = ['login-ztron', 'index-ztron', 'true'] if answer == 'login-ztron' else ['login', 'index', 'paaz']
    for k, v in zip(keys, values):
        replace_config(k, v, config_path)


def create_folder(folder, use_sudo=False):
    if use_sudo:
        cmd = 'sudo mkdir -p %s; sudo chown -R ztron:ztron %s' % (folder, folder)
    else:
        cmd = 'mkdir -p %s;' % folder

    return exec_system_cmd(cmd)


def install_bp_auto():
    service = os.path.join(app_software_path, 'service', apps_detail.get("bp_auto", {}).get("service_name"))
    install_service(service)
    bp_auto_sharedata = ztron_store
    create_folder(bp_auto_sharedata)
    for key, folder_name in zip(['autorunDW', 'sys_workspace', 'app_install_rootSourcePath', 'app_install_rootTargetPath'],
                                ['autorunDW', 'sysWorkspace', 'upload', 'apps']):
        folder = os.path.realpath(os.path.join(bp_auto_sharedata, folder_name))
        create_folder(folder)
        update_config_to_table(key, folder)


def install_biopass_web():
    service = os.path.join(app_software_path, 'service', apps_detail.get("biopass_web", {}).get("service_name"))
    install_service(service)


def get_answer(msg, key=None):
    if key and auto_answer_json.get(key):
        return auto_answer_json.get(key)
    if version_info.major == 3:
        return input(msg)
    else:
        return raw_input(msg)


def get_service_log(service_name, number=20):
    cmd = "sudo journalctl -xe -u %s | tail -%s" %(service_name, number)
    line = "----------------------------   %s  ----------------------------" % service_name
    error_lines = []
    all_lines = [line]
    status = service_manager(service_name, STATUS, True)
    fh = os.popen(cmd, 'r')
    context = fh.read()#.decode('utf-8')
    if status != 0:
        error_lines = [line, context]
    all_lines.append(context)
    fh.close()
    return all_lines, error_lines


def test_rsync():
    rsync_service = "/etc/rsyncd.conf"
    rsync_secret = "/etc/rsyncd.secrets"
    secret_file = "./rsyncd.secrets"
    print("================= rsync config detail ==============")
    with open(rsync_service, 'r') as fh:
        for line in fh.readlines():
            print(line)
    print("====================================================")
    print("start rsync test.....................")
    cmd = "sudo cat /etc/rsyncd.secrets | awk -F':' '{print $2}' > %s; chmod 600 %s" %(secret_file, secret_file)
    exec_system_cmd(cmd)
    cmd = "touch 1; rsync 1 test@127.0.0.1::zlims --password-file=%s" % secret_file
    status = exec_system_cmd(cmd)
    if status != 0:
        print("rsync test........................failed")
    else:
        if os.path.exists(os.path.join(RSYNC_PATH, '1')):
            print("rsync test........................success")
            cmd = "rm 1 ; rm %s" % os.path.join(RSYNC_PATH, '1')
            exec_system_cmd(cmd)
        else:
            print("rsync test........................failed")
            print("Error Reason: rsync path is not correct with config.py")


def check_and_start_postgresql():
    postgre = apps_detail.get("postgresql")
    service_name = postgre.get("service_name")
    status = service_manager(service_name, STATUS, True)
    if status != 0:
        print("Info: postgresql service is not runnint, starting postgresql service.")
        func = postgre.get("install_func")
        func()
        service_manager(service_name, START)


def start_sdk():
    cmd = "sudo docker container ls | grep %s" % sdk_image_name
    fh = os.popen(cmd, 'r')
    context = fh.read()
    fh.close()
    if context:
        print("ZLIMS-SDK is running.")
    else:
        cmd = "cd %s; python installer.py --up" % sdk_path
        exec_system_cmd(cmd)


def stop_sdk():
    cmd = "cd %s; python installer.py --down" % sdk_path
    exec_system_cmd(cmd)


def restart_sdk():
    stop_sdk()
    start_sdk()


def status_sdk():
    cmd = "sudo docker container ls | grep zlims"
    print("\n===================== ZLIMS-SDK container ======================")
    exec_system_cmd(cmd)
    print("==================================================================\n")

apps_detail = {
    "postgresql": {
        "ports": [54321],
        "install_func": install_postgre,
        "service_name": "postgresql-10.12.service"
    },
    "rsync": {
        "ports": [873],
        "install_func": install_rsync,
        "service_name": "rsyncd.service",
        "test_func": test_rsync
    },
    "cromwell": {
        "ports": [9001],
        "install_func": install_cromwell,
        "service_name": "cromwell.service"
    },
    "biopass_web": {
        "ports": [3000],
        "install_func": install_biopass_web,
        "service_name": "biopass_web.service"
    },
    "bp_auto": {
        "ports": [8080],
        "install_func": install_bp_auto,
        "service_name": "bp_auto_app.service"
    },
    "app_client_service": {
        "ports": [],
        "install_func": install_app_client_server,
        "service_name": "ztronAppClientServer.service"
    },
    "app_client_web": {
        "ports": [8091],
        "install_func": install_app_client_web,
        "service_name": "ztronAppClientWeb.service"
    },
    "common_system_manage": {
        "ports": [8089],
        "install_func": install_common_system_manage,
        "service_name": "ztronCommonSystemManage.service"
    },
    "file_manage": {
        "ports": [8041],
        "install_func": install_file_manage,
        "service_name": "ztronFileManage.service"
    },
    "monitor_manage": {
        "ports": [],
        "install_func": install_monitor_manage,
        "service_name": "ztronMonitorSystemManager.service"
    },
    "zlims-sdk": {
        "ports": [],
        "install_func": install_zlims_sdk,
        "service_name": None,
        "service_manager": {
            "start": start_sdk,
            "stop": stop_sdk,
            "restart": restart_sdk,
            "status": status_sdk
        }
    },
    "zlims-pro": {
        "ports": [80, 1886, 2121, 9091, 9090],
        "install_func": install_zlims_pro,
        "service_name": ["nlims_auto.service", "nlims_ftp_auto.service"],
        "sleep_time": 2
    },
    "system_update": {
        "ports": [8062],
        "install_func": install_system_update,
        "service_name": ["ztronSystemUpdate.service", "ztronSystemUpdateWeb.service"]
    }
}


USAGE = """
Usage:
    python %(main)s [install|start|stop|status|restart] [software]

    software defalt:all, value in %(softwares)s

Show error service logs:
    python %(main)s log

if you want show all service log, please execute:
    python %(main)s log --lines=20 --show-all

if you want to test rsync status at locahost, execute:
    python %(main)s test

if you want to update data warehouse path, execute:
    python %(main)s updatedw

if you want to update data sd path, execute:
    python %(main)s updatesd

if you want to config zlims_pro, execute:
    python %(main)s config

if you want to migrate database, execute:
    python %(main)s migrate

if you want to install and config zlims_pro, execute:
    python %(main)s install -c

if you want to install and use last zlims_pro config , execute:
    python %(main)s install -b

first install, setup database init
    python %(main)s setup

""" % ({'main': sys.argv[0], 'softwares': json.dumps(list(apps_detail.keys()))})


def main(argv):
    global auto_answer_json
    try:
        opts, args = getopt.gnu_getopt(argv[1:], "hcb-a:", ["help", "lines=", "show-all"])
        for k, v in opts:
            if '-a' == k:
                try:
                    with open(v, 'r') as fh:
                        auto_answer_json = json.loads(fh.read())
                except Exception as e:
                    print(e)
                break
        if len(args) < 1:
            print(USAGE)
            return 2
        else:
            command = args[0]
            software = 'all'
            if len(args) > 1:
                software = args[1]
            if not(command in [TEST, STATUS, START, STOP, INSTALL, RESTART, LOG, SETUP, UPDATE_DW,
                               CONFIG, CLEARUP, MIGRATE, UPDATE_SD] or software in apps_detail.keys() or command == 'all'):
                print(USAGE)
                return 2
            details = apps_detail
            if software != 'all':
                details = {software: apps_detail.get(software)}
            if command == INSTALL:
                check_and_start_postgresql()
                creat_log_folder()
            for software, detail in details.items():
                service_name = detail.get("service_name")
                services = []
                if service_name:
                    services = service_name
                    if type(service_name) is str:
                        services = [service_name]
     
                if command == SETUP:
                    install_ganglia()
                    install_docker()
                    check_and_install_python3()
                    install_postgre_software()
                    print("Your system environment update, Please execute: source ~/.bashrc")
                    break
                if command == TEST:
                    test_rsync()
                    break
                if command == UPDATE_DW:
                    update_wd()
                    break
                if command == UPDATE_SD:
                    update_sd()
                    break
                if command == CONFIG:
                    config_zlims_pro()
                    break

                if command == CLEARUP:
                    clearup()
                    break
                if command == MIGRATE:
                    migration()
                    break

                if command == LOG:
                    lines = 20
                    show_all = False
                    for o, a in opts:
                        if o in ["--lines"]:
                            lines = a
                        if o in ["--show-all"]:
                            show_all = True
                    for service_name in services:
                        all, err = get_service_log(service_name, lines)
                        if show_all:
                            if all:
                                print("\n".join(all))
                        else:
                            if err:
                                print("\n".join(err))
                    continue

                if command != STATUS:
                    print("%s %-25s................." % (command, software))
                if command == INSTALL:
                    if not os.path.exists(ztron_store):
                        create_folder(ztron_store, use_sudo=True)
                    if not os.path.exists(data_ware_house):
                        create_folder(data_ware_house, use_sudo=True)
                    func = detail.get("install_func")
                    func()

                else:
                    if command == START or command == RESTART:
                        for port in detail.get("ports"):
                            fix_java_home()
                            open_system_port(port)
                    sleep_time = detail.get("sleep_time")
                    for service_name in services:
                        service_manager(service_name, command)
                        if sleep_time:
                            time.sleep(sleep_time)
                    if len(services) < 1 and detail.get("service_manager"):
                        func = detail.get("service_manager").get(command)
                        if func:
                            func()
                if command != STATUS:
                    print("%s %-25s.................done" % (command, software))
            if command == INSTALL:
                for k, v in opts:
                    if '-c' == k:
                        config_zlims_pro()
                    if '-b' == k:
                        recover_config()

    except getopt.GetoptError:
        print(USAGE)
        return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))

