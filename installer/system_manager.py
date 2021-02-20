#!/usr/bin/python
import json
import os
import sys

if len(sys.argv) < 2:
    print("Usage: python %s [sample_id]" % sys.argv[0])
    sys.exit(1)
sample_id = sys.argv[1]
execute_sql = '/home/ztron/wdl_script/execute_sql.sh'
sql = os.path.join(sys.path[0], "get_sample_cromwellid.sh")
search_dir = os.path.join(sys.path[0], "search_dir")
sql="~/.temp.sql"
ss = "SELECT submitcromwell, cromwellid FROM job where jobname like \'%%%s%%\' order by createTime DESC LIMIT 1" % sample_id
os.system("echo \"%s\" > %s"%(ss, sql))
cmd = "%s %s | tail -1" % (execute_sql, sql)

fh = os.popen(cmd, 'r')
content = fh.read().strip()
print(content)
sys.exit(0)
tmp = content.split("\t")
cromwell_ip = tmp[0]
cromwell_ids = tmp[1].split(',')
os.system("rm %s" % sql)


cromwell_url = 'http://%s/api/workflows/v1/%s/metadata'
for cromwell_id in [cromwell_ids[-1]]:
    print("\n\nAnalysis cromwell id: %s" % cromwell_id)
    url = cromwell_url % (cromwell_ip, cromwell_id)
    cmd = 'curl -X GET %s 2>/dev/null' % url
    fh = os.popen(cmd, 'r')
    metadata_str = fh.read()
    try:
        metadata = json.loads(metadata_str)
    except:
        pass
    status = metadata.get("status")
    if status == 'fail':
        print("Get cromwell metadata error. message: %s" %(metadata_str))
    exec_json = metadata
#    print(cromwell_ip, cromwell_id, metadata)
    calls = exec_json.get("calls")
    details = {}
    for key, items in calls.items():
        detail = details.get(key, {})
        execs = []
        for item in items:
            aa = {
                "executionStatus": item.get("executionStatus"),
                "stdout": item.get("stdout"),
                "stderr": item.get("stderr"),
                "jobId": item.get("jobId"),
                "returnCode": item.get("returnCode"),
                "start": item.get("start"),
                "end": item.get("end")
            }
            execs.append(aa)
        details[key] = execs
    print(json.dumps(details, indent=3))
