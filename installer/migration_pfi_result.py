#!/usr/bin/python
import json
import os
import sys

execute_sql = '/home/ztron/app_software/wdl_script/execute_sql.sh'


def get_samples():
    sql = "select s.status, s.sampleid, s.jobname, j.cromwellid, s.tmppath, s.samplename from bp_auto.t_dl_sample s left join bp_auto.t_dl_job j on s.jobname = j.jobname where status = 'completed' and s.configname like 'PFI%';"
    lines = execute_sql([sql], True)[2:][:-2]
    for line in lines:
        tmp = line.split('|')
        sample_id = tmp[1].strip()
        cromwell_id = tmp[3].strip().split(",")[-1]
        path = tmp[4].strip()
        samplename = tmp[5].strip() if tmp[5].strip() else sample_id
        result_path = os.path.join(path) #, samplename)
        if not os.path.exists(result_path):
            print(result_path, "not exists")
        analysis_path = "/storeData/ztron/analysis/pfi_test/%s/call-Pfi/execution/result/Result" % cromwell_id

        if not os.path.exists(analysis_path):
            print(result_path, "analysis path not exists")

        cmd = "cp -fr %s/* %s" % (analysis_path, result_path)
        print(cmd)


def execute_sql(sqls, readlines=False):
    with open("temp.sql", 'w') as fh:
        fh.write("\n".join(sqls))
    cmd = "sh /home/ztron/app_software/wdl_script/execute_sql.sh temp.sql"
    fh = os.popen(cmd, 'r')
    if readlines:
        r = fh.readlines()
    else:
        r = fh.read()
    print("execute log: " + str(r))
    fh.close()
    return r

get_samples()