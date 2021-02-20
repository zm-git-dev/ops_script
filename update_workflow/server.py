import sys
import time
import os

if __name__ == '__main__':
    path = "/storeData/pipeline/public"
    sign_file = os.path.join(path, ".sign")
    sign_done = os.path.join(path, ".sign.done")
    sign_log = os.path.join(path, ".sign.log")
    api = "/home/ztron/app_software/wdl_script/update_workflow/workflow_api.py"
    interval = 2
    total_time = 0
    time_out = 30
    while(True):
        if os.path.exists(sign_file):
            with open(sign_file, 'r') as fh:
                tmp = fh.readline().strip()
                cmd = "python3 %s %s" % (api, tmp)
                f = os.popen(cmd, 'r')
                log = f.read()
                f.close()
                with open(sign_done, 'w') as fh1:
                   fh1.write("done")
                os.remove(sign_file)
            break
        if total_time > time_out:
            break
        total_time += interval
        time.sleep(interval)
