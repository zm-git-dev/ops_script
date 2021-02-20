set -e
if [ "$1" = "" ];then
    echo "Usage: $0 [sql_file]"
    exit 1
fi

DIR="$(cd "$(dirname "$0")" && pwd)"
. $DIR/db.conf

sql=$1

mysql -u$username -p$password -h$host $db_name <$sql && echo "Import success."
