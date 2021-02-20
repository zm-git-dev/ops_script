import paramiko
import json
import subprocess
import os
import sys
import time

package_path = "/home/jenkins_home/workspace"


def sftp_upload_file(host,user,password,server_path, local_path,timeout=10):
    """
    上传文件，注意：不支持文件夹
    :param host: 主机名
    :param user: 用户名
    :param password: 密码
    :param server_path: 远程路径，比如：/home/sdn/tmp.txt
    :param local_path: 本地路径，比如：D:/text.txt
    :param timeout: 超时时间(默认)，必须是int类型
    :return: bool
    """
    try:
        t = paramiko.Transport((host, 22))
        t.banner_timeout = timeout
        t.connect(username=user, password=password)
        sftp = paramiko.SFTPClient.from_transport(t)
        print("uploading %s to server(%s)......" %(local_path, server_path))
        sftp.put(local_path, server_path)
        t.close()
        return True
    except Exception as e:
        print(e)
        return False


def upload_zip(host, version, username="ztron", password="zd2$1#"):
    cmd = 'find %s -name "*%s*.zip"' % (package_path, version)
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    zip_path = str(process.stdout.readlines()[-1], encoding='utf-8').strip()
    zip_name = os.path.basename(zip_path)
    server_path = "/home/ztron/%s" % zip_name
    status = sftp_upload_file(host, username, password, server_path, zip_path)
    if not status:
        raise Exception("上传安装包失败， 请重试")

    return server_path


def update_paaz(host, zip_path, port=22, username="ztron", password="zd2$1#"):
    ssh = paramiko.SSHClient()
    # 允许连接不在know_hosts文件中的主机
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # 建立连接
    ssh.connect(host, username=username, port=port, password=password, timeout=20)
    cmd = "df -h  | grep storeData | grep -v grep"
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd, get_pty=True)
    context = ssh_stdout.read()
    auto_backup = "/home/ztron/backup/auto_deploy"
    cmds = []
    if not context or context == '':
        cmds = ["sudo mkdir -p /data/storeData"]

    answers = {
        "INIT_ZLIMS_PRO_DB": "n",
        "REMOVE_OLD_FILE_MANAGE": "n",
        "INIT_PAAZ_DB": "n",
        "INSTALL_PYTHON3": "y"
    }
    cmds.extend([
            "mkdir -p %s" % auto_backup,
            "sudo rm -fr %s/*" % auto_backup,
            "sh /home/ztron/app_software/wdl_script/backupdb.sh",
            "cp `ls -t /home/ztron/app_software/zlims-pro/backup/*tar.gz | head -1` /home/ztron/dbbackup",
            "python /home/ztron/app_software/installer.py stop",
            "cp /home/ztron/app_software/zlims-pro/nlims/config/application-pro.properties /home/ztron/.config",
            "sudo mv app_software software %s" % auto_backup,
            "unzip %s;" % zip_path,
            "echo '%s' > /home/ztron/app_software/answer.json" % json.dumps(answers).replace("\n", ""),
            "cd /home/ztron/app_software",
            "python installer.py install -b -a /home/ztron/app_software/answer.json",
            "cd /home/ztron/app_software/migration",
            # "sh init.sh",
            "sh migration.sh",
            "rm -fr /home/ztron/app_software/wdl_script/.delete_sql",
            "cp -fr %s/app_software/wdl_script/.delete_sql /home/ztron/app_software/wdl_script" % auto_backup,
            "mv %s/app_software/zlims-pro/backup/* /home/ztron/app_software/zlims-pro/backup" % auto_backup,
            "cd /home/ztron/app_software",
            "python installer.py install monitor_manage",
            "python installer.py start",
            ])
    print("===================", "\n".join(cmds), "===================")
    # 使用这个连接执行命令
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command("\n".join(cmds), get_pty=True)
    # print(ssh_stdout.readline())
    ssh_stdin.write('zd2$1#\n')
    # 获取输出
    print(ssh_stdout.read())
    time.sleep(10)
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('python /home/ztron/app_software/installer.py log', get_pty=True)
    # print(ssh_stdout.readline())
    ssh_stdin.write('zd2$1#\n')
    log = str(ssh_stdout.read(), encoding='utf-8')
    print("service log:", log)
    if "-----------------------" in log:
        raise Exception("部署失败。错误信息:\n" + str(log, encoding='utf-8'))
        sys.exit(2)
    # 关闭连接
    ssh.close()


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python %s <host> <port> <version>" % sys.argv[0])
        sys.exit(0)
    host = sys.argv[1]
    port = sys.argv[2]
    version = sys.argv[3]
    zip_path = upload_zip(host, version) #"/home/ztron/paaz_no_dw.v0.2.5.0.zip" #upload_zip(host, version)
    update_paaz(host, zip_path, port)

