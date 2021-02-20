#
# Install from Horizon production build.
#

#zlims_ui_dir=/var/www/html/zlims
zlims_ui_dir=/var/www/html/
zlims_be_dir=/opt/zlims/be
zlims_venv_dir=/opt/zlims/venv
zlims_log_dir=/var/log/zlims
zlims_apps=/opt/zlims/apps

zlims_config_dir=$zlims_be_dir/configs/official_build

# IP address is safer casue some machine might not have a proper name in its network.
all_local_machine=`hostname -I | xargs`
local_machine=`hostname -I | xargs | awk '{print $1}'`
local_user=`whoami`

importrestdatatype=''
mkdocsproduct=''
num_opts=0
debug=0
verbose=0
to_install=0
to_setup=0
to_restart=0
to_stop=0
to_migrate=0
to_start=0
to_status=0
to_makemigrations=0
to_importrestdata=0
to_mkdocs=0
to_autoans=0
to_collectstatic=0
to_initdatabase=0
to_dbbackup=0
to_dbbackupca=0
to_dbpitr=0

main() {
    process_args "$@"

    if [ $to_autoans -gt 0 ]; then
        setup_autoans
    fi

    if [ $to_stop -gt 0 ]; then
        stop_zlims
    fi

    if [ $to_setup -gt 0 ]; then
        setup_db
        migrate_db
        load_db_data
        create_super_user
        rebuild_zlims_log_dir
        install_nginx_config
        install_uwsgi_service
        install_uwsgi_config
    fi

    if [ $to_install -gt 0 ]; then
        install_ui
        install_be
        install_venv
    fi

    if [ $to_migrate -gt 0 ]; then
        migrate_db
    fi

    if [ $to_restart -gt 0 ]; then
        restart_zlims
    fi

    if [ $to_status -gt 0 ]; then
        status_zlims
    fi

    if [ $to_start -gt 0 ]; then
        start_zlims
    fi

    if [ $to_makemigrations -gt 0 ]; then
        make_migrations_db
    fi

    if [ $to_importrestdata -gt 0 ]; then
        import_rest_data
    fi

    if [ $to_mkdocs -gt 0 ]; then
        mkdocs_for_prod
    fi

    if [ $to_collectstatic -gt 0 ]; then
        collect_static
    fi

    if [ $to_initdatabase -gt 0 ]; then
        stop_zlims
        setup_db
        start_zlims
        migrate_db
        load_db_data
    fi

    if [ $to_dbbackup -gt 0 ]; then
        db_backup
    fi

    if [ $to_dbbackupca -gt 0 ]; then
        db_backup_ca
    fi
    if [ $to_dbpitr -gt 0 ]; then
        db_pitr
    fi
}

isdocker() {
    if grep docker /proc/1/cgroup -qa; then
        true
    else
        false
    fi
}

isdocker() {
    if grep docker /proc/1/cgroup -qa; then
        true
    else
        false
    fi
}

space() {
    echo
}

eon() {
    if [ $verbose -eq 1 ]; then
        set -x
    fi
}

eoff() {
    if [ $verbose -eq 0 ]; then
        set +x
    fi
}

usage()
{
cat << EOF
Usage: $0 [options]

This script installs ZLIMS software to the local machine.

OPTIONS:
    -d    debug
    -h    show help (this message)
    -i    install
    -m    migrate
    -r    restart 
    -s    setup
    -t    stop
    -v    verbose

    --start      start zlims
    --stop       stop zlims
    --restart    restart zlims
    --status     get zlims status
    --makemigrations     Django command makemigrations
    --collectstatic      Django command collectstatic
    --mkdocs=[cdc|all]   Generate online-help documents for specific product
    --autoans=<file>     Use auto answer file
    --importrestdata=[qc|qa|cdc|genebank|...]     import specific REST data
    --initdatabase       init database 
    --dbbackup           backup database 
    --dbbackupca         perform continious archive backup 
    --dbpitr             Point-in-Time recovery using a continious archive backup 

If no option is specified, assume help is needed.

Typical use cases:

(1) To install ZLIMS the very first time (this assumes the Ubuntu OS is setup correctly)

    # Install latest software
    $sh installer.sh -i

    # Setup ZLIMS
    $sh installer.sh -s

    # Restart ZLIMS
    $sh installer.sh -r

    # Load REST data

    $sh installer.sh --importrestdata=[qc|qa|cdc|genebank|...]

    # init database
    $sh installer.sh --initdatabase

    # Generate online-help documents
    $sh installer.sh --mkdocs=[qa|qc|cdc|fox]

    (*) Notes:
    More specific products are on the way


(2) To upgrade existing ZLIMS to the latest (this assumes existing ZLIMS is working correctly)

    # Stop ZLIMS
    $sh installer.sh -t

    # Install latest software
    $sh installer.sh -i

    # Migrate database if needed
    $sh installer.sh -m

    # Restart ZLIMS
    $sh installer.sh -r

See release notes of the target release for detailed instructions.

EOF
}

process_args() {
    while getopts "dhimrstv-:" opt
    do
        case $opt in
            d)
                num_opts=$(($num_opts+1))
                debug=1
                ;;
            h)
                num_opts=$(($num_opts+1))
                usage
                exit 1
                ;;
            i)
                num_opts=$(($num_opts+1))
                to_install=1
                ;;
            m)
                num_opts=$(($num_opts+1))
                to_migrate=1
                ;;
            r)
                num_opts=$(($num_opts+1))
                to_restart=1
                ;;
            s)
                num_opts=$(($num_opts+1))
                to_setup=1
                ;;
            t)
                num_opts=$(($num_opts+1))
                to_stop=1
                ;;
            v)
                num_opts=$(($num_opts+1))
                verbose=1
                eon
                ;;
            #########################################
            # long options
            #########################################
            -)
        case $OPTARG in
                    status )  
                       num_opts=$(($num_opts+1))
                       to_status=1
                       ;;
                    start )  
                       num_opts=$(($num_opts+1))
                       to_start=1
                       ;;
                    stop )  
                       num_opts=$(($num_opts+1))
                       to_stop=1
                       ;;
                    restart )  
                       num_opts=$(($num_opts+1))
                       to_restart=1
                       ;;
                    makemigrations )  
                       num_opts=$(($num_opts+1))
                       to_makemigrations=1
                       ;;
                    importrestdata=* )  
                       importrestdatatype=${OPTARG#*=}
                       num_opts=$(($num_opts+1))
                       to_importrestdata=1
                       ;;
                    mkdocs=* )
                       mkdocsproduct=${OPTARG#*=}
                       num_opts=$(($num_opts+1))
                       to_mkdocs=1
                       ;;
                    autoans=* )
                       autoans_file=${OPTARG#*=}
                       num_opts=$(($num_opts+1))
                       to_autoans=1
                       ;;
                    collectstatic)  
                       num_opts=$(($num_opts+1))
                       to_collectstatic=1
                       ;;
                    initdatabase)
                       num_opts=$(($num_opts+1))
                       to_initdatabase=1
                       ;;
                    dbbackup)
                       num_opts=$(($num_opts+1))
                       to_dbbackup=1
                       ;;
                    dbbackupca)
                       num_opts=$(($num_opts+1))
                       to_dbbackupca=1
                       ;;
                    dbpitr)
                       num_opts=$(($num_opts+1))
                       to_dbpitr=1
                       ;;
                    * )  echo "Illegal option --$OPTARG" >&2; exit 2 ;;
                esac
                ;;
        esac
    done

    if [ $num_opts -eq 0 ]; then
        usage
        exit 1
    fi

    # remove processed options from arguments.
    shift $(($OPTIND-1))
}

setup_autoans() {
    if [ -r $autoans_file ]; then
        . $autoans_file
    else
        echo "Error: cannot access autoans file $autoans_file"
        exit 1
    fi
}

superread() {
    p1="$1"
    vname="installer_autoans_$p1"
    eval vvalue="\$$vname"
    if [ "$vvalue" != "" ]; then
        if [ "$vvalue" = "default" ]; then
            echo ""
        else
            echo "$vvalue"
        fi
        return
    fi

    read ans_tmp
    echo $ans_tmp
}

# Convert upper case to lower case
# $1 is default answer
# $2 is user answer
fixans() {
    if [ "$2" = "" ]; then
         #t=$(tr [A-Z] [a-z] <<< $1)
         t="`echo "$1" | tr [A-Z] [a-z]`"
         echo "$t"
    else
         #t=$(tr [A-Z] [a-z] <<< $2)
         t="`echo "$2" | tr [A-Z] [a-z]`"
         echo "$t"
    fi
}

rebuild_zlims_log_dir() {
    space
    default='no'
    echo "Do you want to reset ZLIMS log directory $zlims_log_dir? (default: $default)"
    autoans=reset_log_dir
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon 

        sudo rm -rf $zlims_log_dir
        sudo mkdir -p $zlims_log_dir
        sudo chown zlims:syslog $zlims_log_dir
        sudo chmod 0777 $zlims_log_dir

        zlims_syslog_file=$zlims_config_dir/48-zlims.conf
        syslog_file=/etc/rsyslog.d/48-zlims.conf

        sudo rm -f $syslog_file
        sudo cp $zlims_syslog_file $syslog_file
        sudo systemctl restart rsyslog

        zlims_logrotate_file=$zlims_config_dir/rsyslog_zlims
        logrotate_file=/etc/logrotate.d/rsyslog_zlims

        sudo rm -f $logrotate_file
        sudo cp $zlims_logrotate_file $logrotate_file

        sudo adduser zlims syslog

        eoff
    fi
}

install_ui() {
    space
    default='yes'
    echo "Do you want to install ZLIMS UI? (default: $default)"
    autoans=install_ui
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space

        eon

        sudo rm -rf $zlims_ui_dir
        sudo mkdir -p $zlims_ui_dir
        sudo chown $local_user $zlims_ui_dir
        unzip ui.zip -d $zlims_ui_dir

        hostname_keyword="__official-build__"
        host="${local_machine}"

        default=$host
        echo "There are the recommended Hostname or IP of the ZLIMS BE ($all_local_machine)"
        echo "Enter hostname or IP of the ZLIMS BE? (default: $default)"
        autoans=enter_hostname_be
        ans=$(superread $autoans)
        ans=$(fixans "$default" "$ans")

        sedline="s/${hostname_keyword}/${ans}/g"

        sed -i "$sedline" $zlims_ui_dir/zlims.environment.config.json


        eoff
    fi
}

install_be() {
    space
    default='yes'
    echo "Do you want to install ZLIMS BE? (default: $default)"
    autoans=install_be
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        sudo rm -rf $zlims_be_dir
        sudo mkdir -p $zlims_be_dir
        sudo chown $local_user $zlims_be_dir
        unzip be.zip -d $zlims_be_dir

        dist_dir=$zlims_be_dir/../dist/
        sudo mkdir -p $dist_dir
        sudo chown $local_user $dist_dir
        #Create version app folder
        sudo mkdir -p $zlims_apps
        sudo mkdir -p $zlims_be_dir/zlims/upload
        sudo ln -s -f $zlims_apps $zlims_be_dir/zlims/upload/apps
        #Make data fresh
        if test -d "${dist_dir}data"
        then
        rm -rf ${dist_dir}data
        fi
        cp -r data $dist_dir
        set_zlims_db_hostname

        eoff
    fi
}

set_zlims_db_hostname(){
    hostname_db="127.0.0.1"
    default=$hostname_db
    echo "Enter hostname or IP of the ZLIMS DB? (default: $default)"
    autoans=enter_hostname_db
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    zlims_values=$zlims_be_dir/zlims/settings/values.py
    db_conf=$zlims_be_dir/scripts/db.conf
    sedline="s/^VALUE_DB_HOST\s*=.*/VALUE_DB_HOST=\"${ans}\"/g"
    sed -i "$sedline" $zlims_values
    sedline="s/hostname=.*/hostname=${ans}/g"
    sed -i "$sedline" $db_conf
}

install_venv() {
    space
    default='yes'
    echo "Do you want to install ZLIMS virtual environment for Python? (default: $default)"
    autoans=install_venv
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        sudo rm -rf $zlims_venv_dir
        sudo mkdir -p $zlims_venv_dir
        sudo chown $local_user $zlims_venv_dir
        unzip venv.zip -d $zlims_venv_dir

        eoff
    fi
}


install_nginx_config() {
    space
    default='no'
    echo "Do you want to install Nginx config file? (default: $default)"
    autoans=install_nginx_config_file
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        zlims_nginx_config_file=$zlims_config_dir/zlims_nginx.conf
        zlims_nginx_default_file=$zlims_config_dir/nginx_default
        zlims_nginx_main_config_file=$zlims_config_dir/nginx.conf
        nginx_config_file="/etc/nginx/sites-enabled/zlims_nginx.conf"
        nginx_default_file="/etc/nginx/sites-available/default"
        nginx_main_config_file="/etc/nginx/nginx.conf"

        sudo rm -f $nginx_config_file
        sudo cp $zlims_nginx_config_file $nginx_config_file
        sudo rm -f $nginx_default_file
        sudo cp $zlims_nginx_default_file $nginx_default_file
        sudo rm -f $nginx_main_config_file
        sudo cp $zlims_nginx_main_config_file $nginx_main_config_file

        eoff
    fi
}

install_uwsgi_service() {
    space
    default='no'
    echo "Do you want to install Uwsgi service file? (default: $default)"
    autoans=install_uwsgi_service_file
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        zlims_uwsgi_service_file=$zlims_config_dir/uwsgi.service
        uwsgi_service_file=/etc/systemd/system/uwsgi.service

        sudo rm -f $uwsgi_service_file
        sudo cp $zlims_uwsgi_service_file $uwsgi_service_file
        sudo systemctl daemon-reload
        sudo systemctl enable uwsgi

        eoff
    fi
}

install_uwsgi_config() {
    space
    default='no'
    echo "Do you want to install Uwsgi config file? (default: $default)"
    autoans=install_uwsgi_config_file
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        uwsgi_config_dir=/etc/uwsgi/vassals/
        uwsgi_config_file=$uwsgi_config_dir/zlims_uwsgi.ini
        zlims_uwsgi_config_file=$zlims_config_dir/zlims_uwsgi.ini

        sudo mkdir -p $uwsgi_config_dir
        sudo rm -f $uwsgi_config_file
        sudo cp $zlims_uwsgi_config_file $uwsgi_config_file

        eoff
    fi
}

status_zlims() {
    systemctl --no-pager status nginx uwsgi
}

start_zlims() {
    sudo service nginx start
    sudo service uwsgi start
}

stop_zlims() {
    sudo service nginx stop
    sudo service uwsgi stop
}

restart_zlims() {
    stop_zlims
    start_zlims
}

setup_db() {
    space
    default='no'
    echo "Do you want to setup database for the first time? (default: $default)"
    autoans=setup_database
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        cd $zlims_be_dir
        sh scripts/db_setup.sh

        eoff
    fi
}

load_db_data() {
    space
    default='no'
    echo "Do you want to load initial data to the database? (default: $default)"
    autoans=load_initial_data
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        . $zlims_venv_dir/bin/activate
        cd $zlims_be_dir
        sh scripts/loadata.sh now
        cat apps/authentication/groups.py | python3 manage.py shell

        eoff
    fi
}

mkdocs_for_prod() {
    space
    default='no'
    echo "Do you want to generate online-help documents for specific product? (default: $default)"
    autoans=generate_online_help
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        . $zlims_venv_dir/bin/activate
        mkdocsproduct=`echo $mkdocsproduct | tr 'A-Z' 'a-z'`
    
        cd $zlims_be_dir/docs/help_cn/docs
        if [ -e "index-$mkdocsproduct.md" ]; then
            cp "index-$mkdocsproduct.md"  index.md
        fi
        cd $zlims_be_dir/docs/help_cn
        cp "mkdocs-$mkdocsproduct.yml"  mkdocs.yml && mkdocs build
        
        cd $zlims_be_dir/docs/help_en/docs
        if [ -e "index-$mkdocsproduct.md" ]; then  
            cp "index-$mkdocsproduct.md"  index.md
        fi
        cd $zlims_be_dir/docs/help_en
        cp "mkdocs-$mkdocsproduct.yml"  mkdocs.yml && mkdocs build
    fi
}

import_rest_data() {
    space
    default='no'
    echo "Do you want to load REST data to ZLIMS? (default: $default)"
    autoans=import_rest_data
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        . $zlims_venv_dir/bin/activate
        cd $zlims_be_dir/scripts
        importrestdatatype=`echo $importrestdatatype | tr 'A-Z' 'a-z'`
        bash import_data.sh $importrestdatatype

        eoff
    fi
}

create_super_user() {
    space
    default='no'
    echo "Do you want to create super user? (default: $default)"
    autoans=create_super_user
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        . $zlims_venv_dir/bin/activate
        cd $zlims_be_dir
        ./manage.py createsuperuser

        eoff
    fi
}

make_migrations_db() {
    space
    default='no'
    echo "Do you want to create database migration scripts if database models have been modified but scripts are not up-to-date? (default: $default)"
    autoans=create_database_migration_scripts
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        . $zlims_venv_dir/bin/activate
        cd $zlims_be_dir
        ./manage.py makemigrations

        eoff
    fi
}

migrate_db() {
    space
    default='yes'
    echo "Do you want to migrate database if updates are avilable? (default: $default)"
    autoans=migrate_database
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        . $zlims_venv_dir/bin/activate
        cd $zlims_be_dir

        . scripts/db.conf
        if psql -tAc  "select string_agg(count||'','' order by n) from (select count(1),0 n from pg_class where relname = 'report' union all select count(1),1 n from django_migrations where app='reports' and name = '0001_report')a" "host=$hostname port=5432 user=$db_user password=$db_pw dbname=$db_name" | grep -q "10"; then
            echo "report table already exist and 0001_report has not been enforced!"
            ./manage.py migrate --fake reports 0001_report
        fi
        ./manage.py migrate

        eoff
    fi
}

#
# Note: Build process already collected static pages.
#
collect_static() {
    space
    default='no'
    echo "Do you want to collect static files for production? (default: $default)"
    autoans=collect_static_files
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        . $zlims_venv_dir/bin/activate
        cd $zlims_be_dir
        ./manage.py collectstatic --noinput

        eoff
    fi
}

db_backup() {
    space
    default='no'
    echo "Do you want to perform a regular DB backup? (default: $default)"
    autoans=backup_database
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        cd $zlims_be_dir
        sh scripts/db_backup.sh

        eoff
    fi
}

db_backup_ca() {
    space
    default='no'
    echo "Do you want to perform a continious archive backup? (default: $default)"
    autoans=perform_continuous_backup
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        cd $zlims_be_dir
        sh scripts/db_backup_cont.sh

        eoff
    fi
}

db_pitr() {
    space
    default='no'
    echo "Do you want to perform a point-in-time recovery using a continious archive backup? (default: $default) \nWARNING!!!: Please be aware that this operation is recommended to be run in a manual mode by admin, running through this script might not be safe for your configuration and if something breaks, it will probably bring the whole system down in a mess. Please proceed at your own risk!!!"
    autoans=perform_point_in_time_recovery
    ans=$(superread $autoans)
    ans=$(fixans "$default" "$ans")
    if [ "$ans" = "yes" ]; then
        space
        eon

        cd $zlims_be_dir
        sh scripts/db_pitr.sh

        eoff
    fi
}


main "$@"
