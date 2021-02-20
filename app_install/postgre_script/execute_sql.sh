set -e
if [ "$1" = "" ];then
    echo "Usage: $0 [sql_file]"
    exit 1
fi

DIR="$(cd "$(dirname "$0")" && pwd)"
. $DIR/db.conf

sql=$1

psql -U $username -h $host -d $db_name <$sql
