import os

install_path = "/home/zebracall/WDL/test/test_install/apps/WDL_Install"
username = "zhouxianqiang"
workflow_name = "megaboltfull"

rule_filename = "%s.rule.json" % workflow_name

config_values = {
    "workflow_name": workflow_name,
    "product_code": workflow_name,
    "username": username,
    "configname": "%s" % workflow_name,
    "wdl_path": os.path.join(install_path, "wdl", "%s.workflow.wdl" % workflow_name),
    "input_json_path": os.path.join(install_path, "input_json", "%s.input.json" % workflow_name),
    "task_path": os.path.join(install_path, "tasks", "%s.task.zip" % workflow_name),
    "note_path": os.path.join(install_path, "notes", "%s.note.json" % workflow_name),
    "bundle_path": os.path.join(install_path, "bundle", "%s.bundle.json" % workflow_name),
    "bundle_key": "",
    "prefix": "",
    "steps": ""
}

rule_ids = []
