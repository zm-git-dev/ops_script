import os
import getopt
import sys
import time

#/usr/lib/lsb/remove_initd /etc/init.d/sgeexecd.p6444

#cp /opt/sysoft/sge/default/common/sgeexecd /etc/init.d/sgeexecd.p6444
#/usr/lib/lsb/install_initd /etc/init.d/sgeexecd.p6444

exec_init = "/etc/init.d/sgeexecd.p6444"
install_path = "/opt/sysoft/sge"


def change_master_hostname(install_path, hostname):
    local_conf_path = os.path.join(install_path, "default/common/local_conf")
    # rm hostname
    cmd = "rm -fr %s/*" % local_conf_path
    os.system(cmd)
    hostname_file = os.path.join(local_conf_path, hostname)
    with open(hostname_file, 'w') as fh:
        context = """
# Version: 8.1.9
# 
# DO NOT MODIFY THIS FILE MANUALLY!
# 
conf_name                    %s
conf_version                 1
mailer                       /bin/mail
xterm                        /usr/bin/xterm
""" % hostname
        fh.write(context)

    spool_conf_path = os.path.join(install_path, "default/spool/qmaster/admin_hosts")
    cmd = "rm -fr %s/*" % spool_conf_path
    os.system(cmd)
    hostname_file = os.path.join(spool_conf_path, hostname)
    with open(hostname_file, 'w') as fh:
        context = """
    # Version: 8.1.9
    # 
    # DO NOT MODIFY THIS FILE MANUALLY!
    # 
    hostname
    %s
""" % hostname
        fh.write(context)


def change_mc():
    num_proc = os.path.join(install_path, "default/spool/qmaster/centry/num_proc")
    virtual_free = os.path.join(install_path, "default/spool/qmaster/centry/virtual_free")
    free = """
    # Version: 8.1.9
# 
# DO NOT MODIFY THIS FILE MANUALLY!
# 
name        virtual_free
shortcut    vf
type        MEMORY
relop       <=
requestable YES
consumable  YES
default     2000G
urgency     0"""
    num = """
    # Version: 8.1.9
# 
# DO NOT MODIFY THIS FILE MANUALLY!
# 
name        num_proc
shortcut    p
type        INT
relop       <=
requestable YES
consumable  YES
default     1000
urgency     100"""


def change_host_group(group, hostnames):
    hostlist_file = os.path.join(install_path, "default/spool/qmaster/hostgroups/%s" % group)
    # auto create
    virtual_free = os.path.join(install_path, "default/spool/qmaster/exec_hosts/MegaBOLT_Workstation")
    free = """
    hostname              MegaBOLT_Workstation
load_scaling          NONE
complex_values        NONE
load_values           NONE
processors            0
reschedule_unknown_list NONE
user_lists            NONE
xuser_lists           NONE
projects              NONE
xprojects             NONE
usage_scaling         NONE
report_variables      NONE"""
    num = """
    # Version: 8.1.9
# 
# DO NOT MODIFY THIS FILE MANUALLY!
# 
group_name %s
hostlist %s""" % (group, " ".join(hostnames))

    with open(hostlist_file, 'w') as fh:
        fh.write(num)


def add_queue(queue, groupname, hostnames):
    change_host_group(groupname, hostnames)
    queue_conf = os.path.join(install_path, "default/spool/qmaster/cqueues/%s" % queue)
    hostname_path = os.path.join(install_path, "default/spool/qmaster/qinstances/%s" % queue)
    all_queue = os.path.join(install_path, "default/spool/qmaster/qinstances/all.q")
    cmd = "mkdir -p %s %s" % (hostname_path, all_queue)
    exec_system_cmd(cmd)
    cpu = "72"
    virtual_free = "128g"
    queue_str = """
    # Version: 8.1.9
# 
# DO NOT MODIFY THIS FILE MANUALLY!
# 
qname                 %(queue)s
hostlist              %(groupname)s
seq_no                0
load_thresholds       np_load_avg=1.75
suspend_thresholds    NONE
nsuspend              1
suspend_interval      00:05:00
priority              0
min_cpu_interval      00:05:00
processors            UNDEFINED
qtype                 BATCH INTERACTIVE
ckpt_list             NONE
pe_list               make smp mpi
rerun                 FALSE
slots                 %(slots)s
tmpdir                /tmp
shell                 /bin/sh
prolog                NONE
epilog                NONE
shell_start_mode      posix_compliant
starter_method        NONE
suspend_method        NONE
resume_method         NONE
terminate_method      NONE
notify                00:00:60
owner_list            NONE
user_lists            NONE
xuser_lists           NONE
subordinate_list      NONE
complex_values        num_proc=%(cpu)s,virtual_free=%(virtual_free)s
projects              NONE
xprojects             NONE
calendar              NONE
initial_state         default
s_rt                  INFINITY
h_rt                  INFINITY
s_cpu                 INFINITY
h_cpu                 INFINITY
s_fsize               INFINITY
h_fsize               INFINITY
s_data                INFINITY
h_data                INFINITY
s_stack               INFINITY
h_stack               INFINITY
s_core                INFINITY
h_core                INFINITY
s_rss                 INFINITY
h_rss                 INFINITY
s_vmem                INFINITY
h_vmem                INFINITY""" % {
        "queue": queue,
        "groupname": groupname,
        "slots": "100",
        "cpu": cpu,
        "virtual_free": virtual_free,

    }
    with open(queue_conf, 'w') as fh:
        fh.write(queue_str)

    mb_str = """
    # Version: 8.1.9
# 
# DO NOT MODIFY THIS FILE MANUALLY!
# 
qname                 %(queue)s
hostname              %(hostname)s
state                 1024
pending_signal        0
pending_signal_del    0
version               %(version)s"""
    for i, hostname in enumerate(hostnames):
        add_submit_host(hostname)
        config = {
            "queue": queue,
            "hostname": hostname,
            "version": 1
        }
        with open(os.path.join(hostname_path, hostname), 'w') as fh:
            fh.write(mb_str % config)
        if i == 0:
            # creat all queue
            with open(os.path.join(all_queue, hostname), 'w') as fh:
                config["queue"] = "all.q"
                fh.write(mb_str % config)

    cmds = [
        "sudo cp /opt/sysoft/sge/default/common/sgeexecd /etc/init.d/sgeexecd.p6444",
        "sudo chmod 755 /etc/init.d/sgeexecd.p6444",
        "sudo ln -s -f /etc/init.d/sgeexecd.p6444 /etc/rc.d/rc3.d/K02sgeexecd.p6444",
        "sudo ln -s -f /etc/init.d/sgeexecd.p6444 /etc/rc.d/rc3.d/S96sgeexecd.p6444"
#        "sudo /usr/lib/lsb/install_initd /etc/init.d/sgeexecd.p6444"
    ]
    exec_system_cmd("\n".join(cmds))
    print("Add queue done. Restart to take effect, Please execute:\n    python %s restartsge" % sys.argv[0])


def stop_sge():
    cmd = "ps -ef | grep sge | grep -v installer.py | awk '{print $2}' | xargs kill -9 2>/dev/null"
    exec_system_cmd(cmd)

def status_sge():
    cmd = "ps -ef | grep sge | grep -v installer.py | grep -v grep"
    fh = os.popen(cmd)
    print(fh.read())
    fh.close()

def test_sge():
    cmd = 'echo "sleep 20" > test.sh ; qsub -l vf=1g,num_proc=1 -q wfq.q test.sh'
    print('echo "sleep 20" > test.sh ; qsub -l vf=1g,num_proc=1 -q wfq.q test.sh')

def start_sge():
    cmd = "/opt/sysoft/sge/bin/lx-amd64/sge_qmaster; /opt/sysoft/sge/bin/lx-amd64/sge_execd"
    exec_system_cmd(cmd)


def add_submit_host(hostname):
    cmd = "mkdir -p %s" % os.path.join(install_path, "default/spool/qmaster/submit_hosts")
    exec_system_cmd(cmd)
    config_file = os.path.join(install_path, "default/spool/qmaster/submit_hosts/%s" % hostname)
    context = """
    # Version: 8.1.9
# 
# DO NOT MODIFY THIS FILE MANUALLY!
# 
hostname              %s""" % hostname
    with open(config_file, 'w') as fh:
        fh.write(context)


def exec_system_cmd(cmd):
    status = os.system(cmd)
    if status != 0:
        print("Warning: exec %s, return code: %s" % (cmd, status))
    return status


def creat_ztron():
    cmds = [
        "sudo groupadd ztron -g 1006",
        "sudo useradd -u 1005 -g 1006 ztron -d /home/ztron -m"
    ]
    status = exec_system_cmd("\n".join(cmds))
    if status != 0:
        print("Create ztron user error, if user have created, but uid,gid not equal 1005,1006. please execute this command:\n")
        print("sudo pkill -u ztron\nsudo usermod -u 1005 ztron\n sudo groupmod -g 1006 ztron\nsudo chown -R ztron:ztron /home/ztron")
    else:
        print("Create ztron user done.")


def fix_hostname(ip, hostname):
    cmd = "sudo echo %s >> /proc/sys/kernel/hostname; echo %s > /etc/hostname" % (hostname, hostname)
    exec_system_cmd(cmd)
    lines = []
    with open("/etc/hosts", 'r') as fh:
        for line in fh.readlines():
            line = line.strip()
            if line.find("localhost") != -1 and not line.strip().startswith("#"):
                lines.append("#" + line)
            elif line.find(hostname) == -1:
                lines.append(line)
        lines.append("%s %s" % (ip, hostname))

    with open("/etc/hosts", 'w') as fh:
        fh.write("\n".join(lines))


def install_sge_dependencies(setup=False):
    lib_path = "/lib64/libhwloc.so.5.7.5"
    if not os.path.exists(lib_path):
        print("libhwloc.so not exists, install libhwloc.so")
        cmd = "cp %s/libhwloc.so* /lib64/" % sys.path[0]
        exec_system_cmd(cmd)
    cmd1 = " sudo yum -y install csh java-1.8.0-openjdk java-1.8.0-openjdk-devel gcc ant automake hwloc-devel openssl-devel libdb-devel pam-devel libXt-devel motif-devel ncurses-libs ncurses-devel "
    cmd2 = " sudo yum -y install ant-junit junit javacc"
    if setup:
        exec_system_cmd(cmd1)
        exec_system_cmd(cmd2)


def install_master(ip="192.168.122.1", hostname="ztron-mgnt-01"):
    sge_package = os.path.join(sys.path[0], "sge")
    cmd = "sudo mkdir -p %s; sudo cp -fr %s/* %s" % (install_path, sge_package, install_path)
    exec_system_cmd(cmd)
    # add sge environment
    cmds = [
        "sudo echo 'export SGE_ROOT=/opt/sysoft/sge' >> /root/.bashrc",
        "sudo echo 'PATH=$PATH:/opt/sysoft/sge/bin/:/opt/sysoft/sge/bin/lx-amd64/' >> /root/.bashrc",
        "sudo echo 'export SGE_ROOT=/opt/sysoft/sge' >> /home/ztron/.bashrc",
        "sudo echo 'PATH=$PATH:/opt/sysoft/sge/bin/:/opt/sysoft/sge/bin/lx-amd64/' >> /home/ztron/.bashrc",
        "sudo chown ztron:ztron /home/ztron/.bashrc"
    ]
    exec_system_cmd("\n".join(cmds))

    # fix hostname
    fix_hostname(ip, hostname)

    change_master_hostname(install_path, hostname)

    cmds = [
        "sudo cp /opt/sysoft/sge/default/common/sgemaster /etc/init.d/sgemaster.p6444",
        "sudo chmod 755 /etc/init.d/sgemaster.p6444",
        "sudo ln -s -f /etc/init.d/sgemaster.p6444 /etc/rc.d/rc3.d/K03sgemaster.p6444",
        "sudo ln -s -f /etc/init.d/sgemaster.p6444 /etc/rc.d/rc3.d/S95sgemaster.p6444",
#        "sudo /usr/lib/lsb/install_initd /etc/init.d/sgemaster.p6444"
    ]
    exec_system_cmd("\n".join(cmds))


def add_host2group(queue, hostname):
    hostname_path = os.path.join(install_path, "default/spool/qmaster/qinstances/%s" % queue)
    lines = []
    with open(os.path.join(hostname_path, hostname), 'r') as fh:
        for line in fh.readlines():
            if line.strip().startswith("hostname"):
                line = line.strip() + " %s\n" % hostname
            lines.append(line)
    with open(os.path.join(hostname_path, hostname), 'w') as fh:
        fh.write("".join(lines))


def get_master_hostline():
    cmd = "cat /etc/hosts | grep -v localhost | grep `hostname`"
    fh = os.popen(cmd, 'r')
    lines = []
    for line in fh.readlines():
        if line not in lines:
            lines.append(line)
    fh.close()
    return "\n".join(lines)


def add_execd(ip, hostname, queue):
    master_host = get_master_hostname()
    add_submit_host(hostname)
    cmd = "cat /opt/sysoft/sge/default/spool/qmaster/cqueues/mb.q | grep hostlist | awk '{print $2}'"
    fh = os.popen(cmd, 'r')
    groupname = fh.read().strip()
    fh.close()
    add_host2group(queue, hostname)
    exec_host_add = "%s\n%s  %s" % (master_host, hostname, ip)
    exec_info = {
        "hostname": hostname,
        "ip": ip,
        "host_add": exec_host_add
    }


def change_hostname(hostname):
    pass


USAGE = """
Usage:
    python %(main)s [all|sethostname|sethosts|setup|installsge|testsge|addztronpath] 


exec all functions:
    python %(main)s all
to install master:
    python %(main)s installmaster [groupname] [ip]

to add submit queue :
    python %(main)s addqueue [queue] [groupname] [hostnames]

to setup sge and create ztron user:
    python %(main)s setup

to start sge:
    python %(main)s startsge
    
to stop sge:
    python %(main)s stopsge

to test SGE :
    python %(main)s testsge

to add path viriable for ztron :
    python %(main)s addztronpath

""" % ({'main': sys.argv[0]})


def main(argv):
    try:
        opts, args = getopt.gnu_getopt(argv[1:], "h", ["help", "lines=", "show-all"])
        if len(args) < 1:
            print(USAGE)
            return 2
        else:
            command = args[0]
            if command == "all":
                install_master()
                add_queue("wfq.q", "@wfq", "ztron-mgnt-01")
                start_sge()
            elif command == "installmaster":
                hostname = "ztron-mgnt-01"
                ip = "192.168.122.1"
                if len(args) > 1:
                    hostname = args[1]
                if len(args) > 2:
                    ip = args[2]
                install_sge_dependencies()
                install_master(ip, hostname)
            elif command == "addqueue":
                queue = "wfq.q"
                groupname = "@wfq"
                hostnames = "ztron-mgnt-01"
                if len(args) > 1:
                    queue = args[1]
                if len(args) > 2:
                    groupname = args[2]
                if len(args) > 3:
                    hostnames = args[3]
                install_sge_dependencies()
                add_queue(queue, groupname, hostnames.split(","))
            elif command == "startsge":
                start_sge()
            elif command == "stopsge":
                stop_sge()
            elif command == "restartsge":
                stop_sge()
                time.sleep(2)
                start_sge()
            elif command == "statussge":
                status_sge()
            elif command == "testsge":
                test_sge()
            elif command == "setup":
                install_sge_dependencies(True)
                creat_ztron()
            else:
                print("Error: Command not find!")
                print(USAGE)
                return 2
            # elif command == "sethosts":
            #     set_hosts()
            # elif command == "installsge":
            #     loadAndMakeSGE()
            # elif command == "testsge":
            #     test_SGE()
            # elif command == "addztronpath":
            #     add_ztron_path()
            # elif command == "chkpy3":
            #     check_and_install_python3()

    except getopt.GetoptError:
        print(USAGE)
        return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv))
