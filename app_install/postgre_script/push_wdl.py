import sys
import os
import re
import json
import datetime
# from common_template import PRODUCT_TEMPLATE, TEMPLATE_TEMPLATE, BUNDLETAG_TEMPLATE, USER_CONFIG_TEMPLATE, RULE_TEMPLATE


GET_RULE_ID_SQL = "SELECT id FROM bp_auto.t_dl_rule ORDER BY id DESC LIMIT 1;"

CHECK_APP_INSTALL_SQL = "SELECT name FROM bp_auto.t_app_install where workflow_code = '%s'"

PRODUCT_TEMPLATE = """INSERT INTO bp_auto.t_dl_product (code, wdl, platform, mail, "user", json, workflow, type, soname, sponame, afterjob, beforejob, spafterjob, spbeforejob, pbeforejob, pafterjob, isPublic, note, poname, extra, step, omics, prefix, taskzip, zone, batch_analysis, upload)
VALUES ('%(product_code)s', '%(wdl_path)s', 'SGE', '%(username)s.genomics.cn', '%(username)s', '%(input_json_path)s', 'write_fastq', '', 'SimpleSingleSO', 'SimpleSingleSPO', 'SampleJobCompletedEvent,SampleCompletedEvent,SampleMvFlagEvent', 'SamplePassEvent', 'SubprojectCheckSampleEvent,SubprojectMvFlagEvent,SubprojectCompletedEvent', '', '', 'ProjectCheckSubprojectEvent,ProjectCompletedEvent', 0, '', 'SimpleSinglePO', '', '%(steps)s', '', '%(prefix)s', '%(task_path)s', 'sz', %(batch_analysis)s, %(upload)s);
"""

TEMPLATE_TEMPLATE = """INSERT INTO bp_auto.t_dl_template (filename, headers, prefix, notepath, check_columns, headers_chn, input_columns, project_column, subproject_column, validator_name, column_count, headersChn)
VALUES ('%(prefix)s.txt', 'None', '%(prefix)s', '%(note_path)s', '', 'None', '', 2, 1, 'BasicTemplateValidator', 0, null);
"""
BUNDLETAG_TEMPLATE = """INSERT INTO bp_auto.t_dl_bundletag (path, tag, zone)
VALUES ('%(bundle_path)s', '%(bundle_key)s', 'sz');
"""

USER_CONFIG_TEMPLATE = """INSERT INTO bp_auto.t_dl_extra_user_config (configname, accounts, cal_paths, code, createtime, default_paths, handover_paths, isPublic, note, store_paths, store_time, username, updateTime, prefix, mailcode, zone)
VALUES ('%(configname)s', '%(username)s', '%(rule_ids)s', '%(product_code)s', '%(create_time)s', '%(rule_ids)s', '%(dv_rule_ids)s', 0, '', '', 30, '%(username)s', '%(create_time)s', '%(prefix)s', 0, 'sz');
"""

RULE_TEMPLATE = """INSERT INTO bp_auto.t_dl_rule (id, omics, workflow, type, subtype, file, thirdtype, extendtype, wdloutputkey)
VALUES (%(id)s, 'genomics', '%(workflow_name)s', '%(type)s', '%(subtype)s', '%(file_pattern)s', null, null, '%(wdl_output_key)s');
"""

PRODUCT_TEMPLATE_DELETE = """DELETE FROM bp_auto.t_dl_product WHERE code = '%(product_code)s';"""

TEMPLATE_TEMPLATE_DELETE = """DELETE FROM bp_auto.t_dl_template WHERE prefix = '%(prefix)s';"""

BUNDLETAG_TEMPLATE_DELETE = """DELETE FROM bp_auto.t_dl_bundletag WHERE tag = '%(bundle_key)s';"""

USER_CONFIG_TEMPLATE_DELETE = """DELETE FROM bp_auto.t_dl_extra_user_config WHERE configname = '%(configname)s';"""

RULE_TEMPLATE_DELETE = """DELETE FROM bp_auto.t_dl_rule WHERE id = '%(id)s';"""

WDL_DEFINITION_TEMPLATE = """insert into bp_auto.wdl_definition (code, name, tasks, workflow)
VALUES ('%(code)s', '%(configname)s', '%(tasks)s'::jsonb, '%(workflow)s'::jsonb)
"""

WDL_DEFINITION_DELETE = """DELETE FROM bp_auto.wdl_definition WHERE code = '%(code)s';"""


def get_wdl_definition(task, workflow, all_sql, delete_sql, config_values):
    try:
        with open(task, 'r') as fh:
            config_values["tasks"] = fh.read()
        with open(workflow, 'r') as fh:
            config_values["workflow"] = fh.read()
        all_sql.append(WDL_DEFINITION_TEMPLATE % config_values)
        delete_sql.append(WDL_DEFINITION_DELETE % config_values)
    except:
        pass


def param_workflow_wdl(wdl):
    flag = False
    output_keys = {}
    prefix = ""
    steps = []
    tasks = []
    with open(wdl, 'r') as fh:
        for line in fh.readlines():
            line = line.strip()
            if line.startswith("#"):
                continue

            workflow_obj = re.search(r'^workflow (\S+) ?\{?$', line)
            if workflow_obj:
                prefix = workflow_obj.groups()[0]

            task_obj = re.search(r'^import ?"([^"]+)"', line)
            if task_obj:
                tasks.append(task_obj.groups()[0])

            step_obj = re.search(r'^call ?(\S+)', line)
            if step_obj:
                step = step_obj.groups()[0]
                step = step.split('.')[-1]
                steps.append(step)

            if line.startswith("output {"):
                flag = True
                continue
            if flag:
                if line.endswith('}'):
                    flag = False
                    continue
                tmp = line.split("=")[0]
                tmp = tmp.strip()
                obj = re.search(r'(\S+)$', tmp)
                if obj:
                    output_key = obj.groups()[0]
                    output_keys[output_key] = ""
    return [output_keys, tasks, steps, prefix]


def execute_sql(sqls, readlines=False):
    with open("temp.sql", 'w') as fh:
        fh.write("\n".join(sqls))
    cmd = "sh execute_sql.sh temp.sql"
    fh = os.popen(cmd, 'r')
    if readlines:
        r = fh.readlines()
    else:
        r = fh.read()
    print("execute log: " + str(r))
    fh.close()
    return r


def get_rule_last_id():
    r = execute_sql([GET_RULE_ID_SQL])
    search_obj = re.search(r'(\S+)\s+\(1 row\)', r)
    sql_id = 1
    if search_obj:
        sql_id = int(search_obj.groups()[0])
    return int(sql_id)


def get_app_conf(app_conf_file):
    app_conf = {}
    with open(app_conf_file, 'r') as fh:
        for line in fh.readlines():
            temp = line.strip().split('=')
            if len(temp) == 2:
                app_conf[temp[0]] = temp[1]
    return app_conf

def create_deploy_path(raw_path, target_path, deploy_shells, require=False):
    deploy_path = os.path.dirname(target_path)
    target_name = os.path.basename(target_path)
    raw_file = os.path.join(raw_path, target_name)
    if require and not os.path.exists(raw_file):
        print("Error: file is not find: %s" % raw_file)
        sys.exit(1)
    deploy_shells.append("mkdir -p %s" % deploy_path)
    deploy_shells.append("cp %s %s" % (raw_file, target_path))
    return raw_file

def get_workflow_name_by_code(product_code):
    lines = execute_sql([CHECK_APP_INSTALL_SQL % product_code], True)
    if len(lines) == 5:
        return lines[2].strip()
    return ""

def remove_exists_old_file(file_list, old_workflow_name):
    cmd = "rm -f "
    for file in file_list:
        path = os.path.dirname(file)
        cmd += "%s/%s* "%(path, old_workflow_name)
    os.system(cmd)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python %s [workflow_wdl] [install_path]\n" % sys.argv[0])
        sys.exit(2)
    workflow_wdl = sys.argv[1]
    if len(sys.argv) > 2:
        install_path = sys.argv[2]
        cmd = "sed -i 's|install_path \?= \?\".\+\"|install_path = \"%s\"|' %s" %(install_path, os.path.join(sys.path[0], "config.py"))
        os.system(cmd)
    rule_json = ""

    workflow_file = os.path.basename(workflow_wdl)
    workflow_name = workflow_file.replace(".workflow", "").replace(".wdl", "")
    raw_file_path = os.path.dirname(workflow_wdl)
    workflow_task_definition = os.path.join(raw_file_path, "tasks.json")
    workflow_definition = os.path.join(raw_file_path, "workflow.json")
    app_conf_file = os.path.join(os.path.dirname(raw_file_path), "app.conf")
    app_conf = get_app_conf(app_conf_file)

    cmd = "sed -i 's/workflow_name \?= \?\"[^\"]\+\"/workflow_name = \"%s\"/' %s" %(workflow_name, os.path.join(sys.path[0], "config.py"))
    os.system(cmd)
    from config import config_values, rule_ids, rule_filename

    now = datetime.datetime.now()
    if app_conf.get('code'):
        config_values['product_code'] = app_conf.get('code')
    if app_conf.get('name'):
        config_values['configname'] = app_conf.get('name')
    config_values['batch_analysis'] = app_conf.get('batch_analysis', 'false')
    config_values['upload'] = app_conf.get('upload', 'false')

    old_workflow_name = get_workflow_name_by_code(config_values['product_code'])
    if old_workflow_name:
        cmd = "sh .delete_sql/%s_%s/delete.sh"%(old_workflow_name, config_values['product_code'])
        os.system(cmd)
        key_list = ["wdl_path","input_json_path","task_path","note_path","bundle_path"]
        file_list = []
        for key in key_list:
            if config_values.get(key, ""):
                file_list.append(config_values[key])
        remove_exists_old_file(file_list, old_workflow_name)

    config_values["create_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
    output_keys, tasks, steps, prefix = param_workflow_wdl(workflow_wdl)
    config_values["steps"] = ",".join(steps)
    rule_json = os.path.join(raw_file_path, rule_filename)
    if len(rule_ids) > 0:
        rule_json = ""

    rules = []
    all_sql = ["BEGIN TRANSACTION;"]
    delete_sql = ["BEGIN TRANSACTION;"]
    dv_rule_ids = []
    if os.path.exists(rule_json):
        with open(rule_json, 'r') as fh:
            rules = json.loads(fh.read())
            last_id = get_rule_last_id()
            for rule in rules:
                output_key = rule.get('wdl_output_key')
                rule["workflow_name"] = config_values.get("workflow_name")
                if not output_key in output_keys.keys():
                    print("Error: rules.json have wdl_output_key: %s, but workflow wdl is not defined!" % output_key)
                    sys.exit(1)
                last_id += 1
                rule['id'] = last_id
                if rule.get("store_to_dv", True) is True:
                    dv_rule_ids.append(last_id)
                rule_ids.append(last_id)
                sql = RULE_TEMPLATE % rule
                all_sql.append(sql)
                delete_sql.append(RULE_TEMPLATE_DELETE % rule)

    if len(rule_ids) == 0:
        print("Warnning: not file store rule be setted.")
    config_values['rule_ids'] = ','.join([str(i) for i in rule_ids])
    config_values['dv_rule_ids'] = ','.join([str(i) for i in dv_rule_ids])
    config_values['prefix'] = prefix
    sql_templates = [PRODUCT_TEMPLATE, TEMPLATE_TEMPLATE, USER_CONFIG_TEMPLATE]
    sql_templates_delete = [PRODUCT_TEMPLATE_DELETE, TEMPLATE_TEMPLATE_DELETE, USER_CONFIG_TEMPLATE_DELETE]
    deploy_shells = []
    wdl_path = config_values.get("wdl_path")
    wdl_deploy_path = os.path.dirname(wdl_path)
    deploy_shells.append("mkdir -p %s" % wdl_deploy_path)
    deploy_shells.append("cp %s %s" %(workflow_wdl, wdl_path))

    input_json_path = config_values.get("input_json_path")
    raw_file = create_deploy_path(raw_file_path, input_json_path, deploy_shells, True)
    bundle_key = ""
    with open(raw_file, 'r') as fh:
        input_json = json.loads(fh.read())
        key = "%s.Bundle" % prefix
        bundle_key = input_json.get(key)
        if bundle_key:
            config_values['bundle_key'] = bundle_key
            sql_templates.append(BUNDLETAG_TEMPLATE)
            sql_templates_delete.append(BUNDLETAG_TEMPLATE_DELETE)
        else:
            print("Info: input json not set bundle. bundle key: %s is no find." % key)
    note_path = config_values.get("note_path")
    create_deploy_path(raw_file_path, note_path, deploy_shells)
    if bundle_key:
        bundle_path = config_values.get("bundle_path")
        create_deploy_path(raw_file_path, bundle_path, deploy_shells, True)

    task_path = config_values.get("task_path")
    task_files = []
    for task in tasks:
        task_files.append(os.path.join(raw_file_path, task))
    task_deploy_dir = os.path.dirname(task_path)
    deploy_shells.append("mkdir -p %s" % task_deploy_dir)
    deploy_shells.append("zip -j %s %s" % (task_path, " ".join(task_files)))
    for template, template_delete in zip(sql_templates, sql_templates_delete):
        all_sql.append(template % config_values)
        delete_sql.append(template_delete % config_values)
    with open(".temp.sh", 'w') as fh:
        fh.write("\n".join(deploy_shells))
    os.system(";".join(deploy_shells))
    with open(".temp.sql", 'w') as fh:
        fh.write("\n".join(all_sql))
    get_wdl_definition(workflow_task_definition, workflow_definition, all_sql, delete_sql, config_values)
    all_sql.append("END TRANSACTION;")
    execute_sql(all_sql)
    delete_path = os.path.join(".delete_sql", "%s_%s" % (config_values['configname'], config_values['product_code']))
    cmd = "mkdir -p %s" % delete_path
    os.system(cmd)
    delete_sql.append("END TRANSACTION;")
    delete_sql_path = os.path.join(sys.path[0], delete_path, "delete.sql")
    delete_run_sh = os.path.join(sys.path[0], delete_path, "delete.sh")
    with open(delete_sql_path, 'w') as fh:
        fh.write("\n".join(delete_sql))
    with open(delete_run_sh, 'w') as fh:
        fh.write("sh %s %s" % (os.path.join(sys.path[0], "execute_sql.sh"), delete_sql_path))
    print("\n\n========================================\nCreate product success.\nFor delete product, you can execute:  %s" % delete_run_sh)
