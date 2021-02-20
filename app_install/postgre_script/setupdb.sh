set -e
#if [ "$1" = "" ];then
#    echo "Usage: $0 [sql_file]"
#    exit 1
#fi

DIR="$(cd "$(dirname "$0")" && pwd)"
. $DIR/db.conf

sql=$DIR/.tmp.sql
echo "select * from information_schema.SCHEMATA where SCHEMA_NAME = '${db_name}'" > $sql
db_exists=`mysql -uroot -p$root_password -h$host < $sql`
if [ "$db_exists" != "" ];
then
    echo "Database have exists, backupdb....."
    sh $DIR/backupdb.sh
    echo "drop database ${db_name}" > $sql
    echo "Drop database ${db_name}...."
    mysql -uroot -p$root_password -h$host < $sql
fi

echo "CREATE DATABASE ${db_name} DEFAULT CHARSET utf8 COLLATE utf8_general_ci;" > $sql
echo "Create database ${db_name}....."
mysql -uroot -p$root_password -h$host < $sql
echo "Grant privity for user....."
echo "grant all on ${db_name}.* to  ${username}@ identified by '${password}';" > $sql
mysql -uroot -p$root_password -h$host < $sql
echo "done."


