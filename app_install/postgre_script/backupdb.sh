set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
. $DIR/db.conf

echo "Backup $db_name database..."

mkdir -p $backup_path
pg_dump -c --column-inserts "host=$host port=54321 user=$username password=$password dbname=$db_name"  > $backup_path/$db_name$(date +%Y%m%d%H%M%S).sql
echo "DB Backup can be found in $backup_path"
