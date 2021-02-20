import sys
import time
import os

path = "/storeData/pipeline/public"
sign_file = os.path.join(path, ".sign")
sign_done = os.path.join(path, ".sign.done")
sign_log = os.path.join(path, ".sign.log")

def exit_test():
    try:
        os.remove(sign_done)
        os.remove(sign_log)
        os.remove(sign_file)
    except:
        pass
    sys.exit(0)


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print("Usage: python %s [product_name] [new_workflow] [task_resource] [workflow_config]" % sys.argv[0])
        sys.exit(0)
    product_name = sys.argv[1]
    new_workflow = os.path.realpath(sys.argv[2])
    task_resource = os.path.realpath(sys.argv[3])
    workflow_config = os.path.realpath(sys.argv[4])
    try:
        os.remove(sign_done)
    except:
        pass
    with open(sign_file, 'w') as fh:
        fh.write("%s\t%s\t%s\t%s" % (product_name, new_workflow, task_resource, workflow_config))
    interval = 2
    total_time = 0
    time_out = 5 * 60
    while(True):
        if os.path.exists(sign_done):
            with open(sign_log, 'r') as fh:
                print(fh.read())
            print("Install.........Done")
            exit_test()
            
        if total_time > time_out:
            print("Error: timeout.")
            exit_test()
        total_time += interval
        time.sleep(interval)
