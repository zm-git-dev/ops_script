import json
import re
import sys
import os
from shutil import copyfile, copytree

TOOLS_WDL = os.path.join(os.path.realpath(sys.path[0]), "tools.wdl")
TOOLS_PY = os.path.join(os.path.realpath(sys.path[0]), "tools.py")
GET_RULE_ID_SQL = "SELECT id FROM bp_auto.t_dl_rule ORDER BY id DESC LIMIT 1;"
RULE_TEMPLATE = """INSERT INTO bp_auto.t_dl_rule (id, omics, workflow, type, subtype, file, thirdtype, extendtype, wdloutputkey)
VALUES (%(id)s, 'genomics', '%(workflow_name)s', '%(type)s', '%(subtype)s', '%(file_pattern)s', null, null, '%(wdl_output_key)s');
"""
UPDATE_USER_CONFIG_TEMPLATE = """UPDATE bp_auto.t_dl_extra_user_config set cal_paths = '%(rule_ids)s', default_paths = '%(rule_ids)s' , handover_paths='%(dv_rule_ids)s' 
WHERE configname = '%(configname)s';
"""
STANDARD_TEMPLATE = """INSERT INTO bp_auto.t_dl_qc_standards(key, discription_cn, discription_en, display_cn, display_en, standard, quality_control_result, display_order)
VALUES ('%(key)s', '%(discription_cn)s', '%(discription_en)s', '%(display_cn)s', '%(display_en)s', '%(standard)s', true, %(order)s);
"""
UPDATE_STANDARD_TEMPLATE = """UPDATE bp_auto.t_dl_qc_standards set discription_cn = '%(discription_cn)s', discription_en = '%(discription_en)s',
display_cn = '%(display_cn)s', display_en = '%(display_en)s', standard = '%(standard)s' where key = '%(key)s';
"""

UPDATE_TEMPLATE_TEMPLATE = """UPDATE  bp_auto.t_dl_template set prefix = '%(prefix)s' where prefix = '%(origin_prefix)s';
"""
UPDATE_PRODUCT_TEMPLATE = """UPDATE  bp_auto.t_dl_product set prefix = '%(prefix)s' where prefix = '%(origin_prefix)s';
"""
GET_STANDARD_BY_KEY = "SELECT * from bp_auto.t_dl_qc_standards where key = '%(key)s';"


def prepare_expression(expression_str):
    sample_metadata = []
    uniq_keys = {}
    uniq = {}
    for find_str in re.findall(r'\$\{[^\}]+\}', expression_str):
        if find_str.startswith("${sample.") and find_str not in uniq.keys():
            sample_metadata.append({
               "value_from": find_str,
               "required": True,
               "key": find_str.split(".")[-1].replace("}", ""),
                "map_key": "",
                "type": "String",
            })
            if find_str in ["${sample.read1}", "${sample.read2}", "${sample.metadata.files.read1}", "${sample.metadata.files.read2}"]:
                sample_metadata[-1]["map_key"] = ","
            if re.search(r'\.files\.', find_str):
                sample_metadata[-1]["type"] = "File"
            if find_str in ["${sample.read2}", "${sample.metadata.files.read2}"]:
                sample_metadata[-1]["required"] = False
            uniq[find_str] = ""
            uniq_keys[find_str.split(".")[-1].replace("}", "")] = find_str.replace('$', '').replace('{', '').replace('}', '')
            expression_str = expression_str.replace(find_str, find_str.replace('$', '%').replace('{', '(').replace('}', ')') + 's')
    return expression_str, sample_metadata, uniq_keys


def add_prepare2workflow(workflow_file, wdl):
    parameters, workflow_name = get_workflow_inputs(workflow_file)
    # workflow_file_path = os.path.dirname(workflow_file)
    # install_path = os.path.join(os.path.dirname(workflow_file_path), workflow_name, "bin")
    with open(workflow_file, 'r') as fh:
        workflow_content = fh.read()
        expression_str, sample_metadata, uniq_keys = prepare_expression(workflow_content)
        variants = {}
        for k, v in uniq_keys.items():
            variants[v] = 'PrepareInput.param["%s"]' % k
        expression_str = expression_str % variants
        call_prepare = """
  call tools.PrepareInput {
    input:
    data                = Data,
    param_json          = param_json,
    tools_main          = "%s",
  }
        """ % get_tools_path(workflow_name, wdl)
        expression_str = expression_str.replace("call ", "%scall " % call_prepare, 1)
        search_obj = re.search(r'(\s{1,}input\s{0,}\{)', expression_str)
        input_str = search_obj.groups()[0]
        expression_str = expression_str.replace(input_str, "%s\nArray[Array[String]] Data\nString SampleID\n" % input_str, 1)
        new_workflow_content = expression_str.replace("import ", "import \"tools.wdl\"\nimport ", 1)
        config_json = {
            "input_files": [],
            "params": sample_metadata
        }
        new_metadata = []
        for i in  sample_metadata:
            if i["value_from"] not in ["${sample.read1}"]:
                new_metadata.append(i)
        note_json = {
            "parameters": parameters,
            "input_files": [{
                "file_name": "params_file",
                "no_need_create": True,
                "columns": new_metadata
            }]
        }
        input_json = {
            "%s.SampleID" % workflow_name: "$SampleID$",
            "%s.Data" % workflow_name: "$Data$",
        }
        for item in parameters:
            if item["default"] and item["default"] != "":
                input_json[item["key"]] = item["default"]
        return note_json, new_workflow_content, config_json, workflow_name, input_json
        # print(json.dumps(note_json, indent=3))
        # print(expression_str)


def get_workflow_inputs(workflow_file):
    input_begin = False
    parameters = []
    workflow_name = ""
    with open(workflow_file, 'r') as fh:
        for line in fh.readlines():
            search_obj = re.search(r'^workflow\s{1,}(\S+)\s{0,}\{{0,1}', line.strip())
            if search_obj:
                workflow_name = search_obj.groups()[0]
            search_obj = re.search(r'^input\s{0,}\{{0,1}', line.strip())
            if search_obj:
                input_begin = True
                continue
            search_obj = re.search(r'\}', line.strip())
            if input_begin and search_obj:
                break
            if input_begin:
                if line.strip() != "":
                    items = line.strip().split("=")
                    tmp = re.split('\s+', items[0].strip())
                    if len(tmp) < 2:
                        raise Exception("Error: can not get input type.")
                    parameter = {
                        "order": 1,
                        "key": "%s.%s" % (workflow_name, tmp[1]),
                        "map_key": "",
                        "type": tmp[0],
                        "required": False,
                        "display_name_en": tmp[1],
                        "display_name_cn": tmp[1],
                        "description_en": tmp[1],
                        "description_cn": tmp[1],
                        "validation_rule": "",
                        "default": "",
                        "value_from": ""
                    }
                    if len(items) > 1:
                        parameter["default"] = items[1].strip().replace("'", "").replace('"', "")
                        if tmp[0] == "Int":
                            parameter["default"] = int(parameter["default"])
                    parameters.append(parameter)
    return parameters, workflow_name


def execute_sql(sqls, readlines=False):
    sql_file = ".temp.sql"
    with open(sql_file, 'w') as fh:
        fh.write("\n".join(sqls))
    cmd = "sh /home/ztron/app_software/wdl_script/execute_sql.sh %s" % sql_file
    fh = os.popen(cmd, 'r')
    if readlines:
        r = fh.readlines()
    else:
        r = fh.read()
#    print("execute log: " + str(r))
    fh.close()
    cmd = "rm %s" % sql_file
    os.system(cmd)
    return r


def get_standard_status(key):
    r = execute_sql([GET_STANDARD_BY_KEY % {"key": key}], True)
    if len(r) > 4:
        return True
    return False


def get_rule_last_id():
    r = execute_sql([GET_RULE_ID_SQL])
    search_obj = re.search(r'(\S+)\s+\(1 row\)', r)
    sql_id = 1
    if search_obj:
        sql_id = int(search_obj.groups()[0])
    return int(sql_id)


def get_product(product_name):
    sql = "select p.wdl, p.json, p.taskzip, t.notepath, p.prefix from bp_auto.t_dl_extra_user_config e left join bp_auto.t_dl_product p on e.code = p.code left join bp_auto.t_dl_template t on t.prefix = p.prefix where e.configname = '%s';" % product_name
    lines = execute_sql([sql], True)
    if len(lines) > 2:
        tmp = lines[2].strip().split("|")
        print(tmp)
        wdl = tmp[0].strip()
        json_file = tmp[1].strip()
        taskzip = tmp[2].strip()
        notepath = tmp[3].strip()
        prefix = tmp[4].strip()
        return wdl, json_file, taskzip, notepath, prefix
    else:
        raise Exception("Error: product is no find.")


def get_tools_path(workflow_name, wdl):
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(wdl))), workflow_name, "bin", "tools.py")


def update_workflow(product_name, new_workflow, task_resource, workflow_config):
    with open(workflow_config, 'r') as fh:
        config = json.loads(fh.read())
    
    wdl, input_json_file, taskzip, notepath, origin_prefix = get_product(product_name)
    note_json, new_workflow_content, config_json, workflow_name, input_json = add_prepare2workflow(new_workflow, wdl)
    user_wk = workflow_name
    with open(new_workflow, 'r') as fh:
        new_workflow_content = fh.read()
        search_obj = re.search(r'\s{0,}(workflow\s+\S+\s{0,}\{)', new_workflow_content)
        output_str = search_obj.groups()[0]
        new_workflow_content = new_workflow_content.replace(output_str, "\nworkflow %s {" % origin_prefix, 1)
        new_wdl = ".tmp.wdl"
        with open(new_wdl, 'w') as fh:
            fh.write(new_workflow_content)
    note_json, new_workflow_content, config_json, workflow_name, input_json = add_prepare2workflow(new_wdl, wdl)

    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(wdl))), workflow_name, "bin")
    tools_file = get_tools_path(workflow_name, wdl)
    print(wdl, input_json_file, taskzip, notepath)
    # update product prefix
#    all_sql = ["BEGIN TRANSACTION;"]
#    variants = {"prefix": workflow_name, "origin_prefix": origin_prefix}
#    all_sql.append(UPDATE_TEMPLATE_TEMPLATE % variants)
#    all_sql.append(UPDATE_PRODUCT_TEMPLATE % variants)
#    all_sql.append("END TRANSACTION;")
#    execute_sql(all_sql)
    # prepare wdl tasks
    cmd = "rm -fr .workflow_tmp ; mkdir -p .workflow_tmp; cd .workflow_tmp; unzip %s ; cp %s ./; rm %s; zip -r %s ./" % (task_resource, TOOLS_WDL, taskzip, taskzip)
    print(cmd)
    os.system(cmd)
    # prepare tools config
    cmd = "mkdir -p %s; cp %s %s;" % (config_path, TOOLS_PY, tools_file)
    os.system(cmd)
    config_json_file = os.path.join(config_path, "config.json")
    config_json["get_qc_rules"] = config.get("get_qc_rules", [])
    with open(config_json_file, 'w', encoding='UTF-8') as fh:
        fh.write(json.dumps(config_json, indent=3))
    # prepare note json
    with open(notepath, 'w', encoding='UTF-8') as fh:
        fh.write(json.dumps(note_json, indent=3))

    # prepare input json
    with open(input_json_file, 'w', encoding='UTF-8') as fh:
        fh.write(json.dumps(input_json, indent=3))

    # update workflow rules
    if len(config.get("archive_rules", [])) > 0:
        for item in config.get("archive_rules", []):
            item["wdl_output_key"] = item["wdl_output_key"].replace("%s."%user_wk, "%s." % origin_prefix)
        update_rules(config.get("archive_rules", []), product_name, workflow_name)
    else:
        print("Warnning: workflow have no result file to archive.")

    # get qc values from outputs
    if len(config.get("get_qc_rules", [])) > 0:
        variants = []
        all_sql = ["BEGIN TRANSACTION;"]
        for i, qc_rule in enumerate(config.get("get_qc_rules", [])):
            target_file = qc_rule.get("target_file", "")
            search_obj = re.search(r'\$\{([^\}]+)\}', target_file)
            key = qc_rule.get("key", "")
#            key = "%s_%s" % (workflow_name, qc_rule.get("key", ""))
            attrs = {
                "key": key,
                "discription_cn": qc_rule.get("discription_cn", key),
                "discription_en": qc_rule.get("discription_en", key),
                "display_cn": qc_rule.get("display_cn", key),
                "display_en": qc_rule.get("display_en", key),
                "standard": qc_rule.get("standard"),
                "order": i+1,
            }
            if get_standard_status(key):
                all_sql.append(UPDATE_STANDARD_TEMPLATE % attrs)
            else:
                all_sql.append(STANDARD_TEMPLATE % attrs)
            if search_obj:
                variant = search_obj.groups()[0]
                variants.append('"%s": %s' % (variant, variant))
        all_sql.append("END TRANSACTION;")
        print(all_sql)
        execute_sql(all_sql)
        get_qc_values = """
        call tools.GetManyQcValues
        {
            input:
                data = Data,
                       result_dir = {%s},
                       tools_main = "%s",
        }
        """ % (", ".join(variants), os.path.join(config_path, "tools.py"))
        search_obj = re.search(r'\s{0,}(output\s{0,}\{)', new_workflow_content)
        output_str = search_obj.groups()[0]
        new_workflow_content = new_workflow_content.replace(output_str, "%s\n%s" % (get_qc_values, output_str), 1)
        workflow_qc = """
    Map[String, String] QC_VALUES = GetManyQcValues.qc_values
    Map[String, String] QC_STANDARDS = GetManyQcValues.standards
"""
        new_workflow_content = new_workflow_content.replace(output_str, "%s\n%s" % (output_str, workflow_qc), 1)
    # prepare workflow wdl
    with open(wdl, 'w') as fh:
        fh.write(new_workflow_content)


def update_rules(rules, product_name, workflow_name):
    last_id = get_rule_last_id()
    rule_ids = []
    dv_rule_ids = []
    all_sql = ["BEGIN TRANSACTION;"]
    for rule in rules:
        # output_key = rule.get('wdl_output_key')
        # rule["workflow_name"] = config_values.get("workflow_name")
        # if not output_key in output_keys.keys():
        #     print("Error: rules.json have wdl_output_key: %s, but workflow wdl is not defined!" % output_key)
        #     sys.exit(1)
        last_id += 1
        rule['id'] = last_id
        rule['workflow_name'] = workflow_name
        rule['subtype'] = rule.get('subtype', "")
        if rule.get("store_to_dv", True) is True:
            dv_rule_ids.append(last_id)
        rule_ids.append(last_id)
        rule["wdl_output_key"] = rule["wdl_output_key"].replace("%s."%workflow_name, "")
        sql = RULE_TEMPLATE % rule
        all_sql.append(sql)
    all_sql.append(UPDATE_USER_CONFIG_TEMPLATE % { "rule_ids": ",".join([str(i) for i in rule_ids]), "dv_rule_ids": ",".join([str(i) for i in dv_rule_ids]), "configname": product_name})
    all_sql.append("END TRANSACTION;")
    print(all_sql)
    execute_sql(all_sql)


if __name__ == '__main__':
    if len(sys.argv) < 5:
        print("Usage: python %s [product_name] [new_workflow] [task_resource] [workflow_config]" % sys.argv[0])
        sys.exit(0)
    product_name = sys.argv[1]
    new_workflow = sys.argv[2]
    task_resource = os.path.realpath(sys.argv[3])
    workflow_config = os.path.realpath(sys.argv[4])
    update_workflow(product_name, new_workflow, task_resource, workflow_config)
