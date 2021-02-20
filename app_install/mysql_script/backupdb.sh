set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
. $DIR/db.conf

echo "Backup $db_name database..."

mkdir -p $backup_path
mysqldump -u${username} --databases $db_name -p${password} -h${host} > $backup_path/$db_name$(date +%Y%m%d%H%M%S).sql
echo "DB Backup can be found in $backup_path"
