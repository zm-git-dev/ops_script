# note
that script must run as root acount
# install sge at ztron
sh ztron_lite_install.sh
# install sge at megabolt
sh megabolt_install.sh
# sge installer.py
Usage:
    python installer.py [all|sethostname|sethosts|setup|installsge|testsge|addztronpath] 


exec all functions:
    python installer.py all
to install master:
    python installer.py installmaster [groupname] [ip]

to add submit queue :
    python installer.py addqueue [queue] [groupname] [hostnames]

to setup sge and create ztron user:
    python installer.py setup

to start sge:
    python installer.py startsge
    
to stop sge:
    python installer.py stopsge

to test SGE :
    python installer.py testsge

to add path viriable for ztron :
    python installer.py addztronpath
