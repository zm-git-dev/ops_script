import json
import re
import sys
import os
from shutil import copyfile, copytree

# prepare_config = {
#     "input_files": [],
#     "params": []
# }
prepare_param = 'PrepareInput.param["%s"]'
default_adapter_3 = "AAGTCGGAGGCCAAGCGGTCTTAGGAAGACAA"
default_adapter_5 = "AAGTCGGATCGTAGCCATGTCGTTCTGTGAGCCAAGGAGTTG"


def check_need_adapter(expression_str):
    if not expression_str:
        return
    global need_adapter3, need_adapter5
    if len(re.findall(r'\$\{adapter3\}', expression_str)):
        need_adapter3 = True
    if len(re.findall(r'\$\{adapter5\}', expression_str)):
        need_adapter5 = True


def load_tasks(task_json):
    with open(task_json, 'r', encoding='UTF-8') as fh:
        return json.loads(fh.read())


def get_flowcell_input():
    return {
        "task_input": "String flowcell_id\nString lane_id\nString barcode_id",
        "workflow_calculate": "String flowcell_id = Data[0][4]\nString lane_id = Data[0][5]\nString barcode_id = Data[0][3]",
        "workflow_call_input": "flowcell_id = flowcell_id,\nlane_id = lane_id,\nbarcode_id = barcode_id,\n"
    }


def remove_dup(params, input_files):
    uniq_key = []
    new_params = []
    for item in params:
        k = item.get("value_from")
        if not k or k not in uniq_key:
            new_params.append(item)
            uniq_key.append(k)
    for input_file in input_files:
        new_columns = []
        for item in input_file.get("columns", []):
            k = item.get("value_from")
            if not k or k not in uniq_key:
                new_columns.append(item)
                uniq_key.append(k)
        input_file["columns"] = new_columns
    return new_params, input_files


def decode_workflow(workflow, tasks):
    global prepare_config
    workflow_tasks = []
    workflow_code = workflow.get("workflow_code")
    workflow_name = workflow.get("workflow_name")
    batch_analysis = workflow.get("batch_analysis")
    steps = workflow.get("steps")
    import_wdl = ''
    call_tasks = ''
    outputs = ''
    inputs = ''
    calculate = ''
    workflow_note = []
    input_files = []
    rules = []
    input_json = {
        "%s.SampleID" % workflow_name: "$SampleID$",
        "%s.Data" % workflow_name: "$Data$"
    }
    wdl_path = os.path.join(sys.path[0], workflow_name, "workflow")
    try:
        os.remove(wdl_path)
    except Exception as e:
        print(e)
    if not os.path.exists(wdl_path):
        os.makedirs(wdl_path)
    for step in steps:
        task_id = step.get("task_id")
        task_filename = task_id + ".wdl"
        task_file = os.path.join(wdl_path, task_filename)
        task_detail, task = create_task_wdl(step, tasks, workflow_name, task_file)
        workflow_tasks.append(task)
        input_mapping = step.get("input_mapping", {})
        step_input = ''
        for key, value in input_mapping.items():
            step_input += '%s = %s,\n' % (key, value)
        import_wdl += "import \"%s\"\n" % task_filename
        call_tasks += '''
    call %s.%s {
        input:
        sample_id = sample_id,
        %s
    }
    ''' % (task_id, task_id, task_detail.get("workflow_call_input", "") + step_input)
        archive_rules = task_detail.get("archive_rules", [])
        prepare_config["archive_rules"].extend(archive_rules)

        lookup_definition = task.get("lookup_definition", [])
        prepare_config["lookup_definition"].extend(lookup_definition)

        if task.get("capture_data"):
            prepare_config["capture_data"] = task.get("capture_data")
        archive_parameters = None
        input_files.extend(task_detail.get("input_files", []))
        for archive_rule in task_detail.get("archive_rules", []):
            ## get parameters value
            origin_path = archive_rule.get("origin_path", "")
            search_obj = re.search(r'\$\{output\.([^\}]+)\}', origin_path)
            if search_obj:
                archive_parameters = search_obj.groups()[0]
        if archive_parameters:
            call_tasks += '''
    call tools.ResultArchive {
        input:
        data                = Data,
        result_dir          = %s.%s,
        tools_main          = tools_main,
    }
    ''' % (task_id, archive_parameters)

        get_qc_rules = task_detail.get("get_qc_rules", [])
        prepare_config["get_qc_rules"].extend(get_qc_rules)
        get_qc_parameters = None
        for get_qc_rule in task_detail.get("get_qc_rules", []):
            ## get parameters value
            target_file = get_qc_rule.get("target_file", "")
            search_obj = re.search(r'\$\{output\.([^\}]+)\}', target_file)
            if search_obj:
                get_qc_parameters = search_obj.groups()[0]
        if get_qc_parameters:
            call_tasks += '''
    call tools.GetQcValues {
        input:
        data                = Data,
        result_dir          = %s.%s,
        tools_main          = tools_main,
    }
    ''' % (task_id, get_qc_parameters)
            outputs += "Map[String, String] QC_VALUES = GetQcValues.qc_values\n"
            outputs += "Map[String, String] QC_STANDARDS = GetQcValues.standards\n"
        if task.get("update_flow") is True:
            call_tasks += '''
            call tools.UpdateFlow {
                input:
                data                = Data,
                result_dir          = %s.result,
                tools_main          = tools_main,
            }
            ''' % task_id
        outputs += task_detail.get("workflow_output", "")
        calculate += task_detail.get("workflow_calculate", "")
        input_json.update(task_detail.get("input_json", {}))
        rules.extend(task_detail.get("rules", []))
        for parameter in task_detail.get("parameters", []):
            temp = parameter.copy()
            temp["key"] = "%s.%s.%s" % (workflow_name, task_id, temp["key"])
            value_from = temp.get("value_from", "")
            if value_from.startswith("code#") or re.search(r'\$\{sample\.metadata\.', value_from) or parameter.get("ui_no_need") is True: #temp.get("value_from"):
                continue
            workflow_note.append(temp)
    for op in workflow.get("output", []):
        outputs += "%s %s = %s\n" % (op.get("type"), op.get("key"), op.get("value"))
    with open(os.path.join(wdl_path, workflow_name+".workflow.wdl"), 'w') as fh:
        workflow_wdl_template = get_workflow_wdl_template()
        workflow_wdl = workflow_wdl_template % {
            "workflow_id": workflow_name,
            "import_wdl": import_wdl,
            "call_tasks": call_tasks,
            "outputs": outputs,
            "inputs": inputs,
            "calculate": calculate,
        }
        fh.write(workflow_wdl)
    if need_adapter3:
        input_json["%s.PrepareInput.adapter3" % workflow_name] = default_adapter_3
        workflow_note.append({
          "description_cn": "3端接头序列",
          "key": "%s.PrepareInput.adapter3" % workflow_name,
          "required": False,
          "value_from": "",
          "default": default_adapter_3,
          "map_key": "",
          "description_en": "Adapter3",
          "type": "String",
          "order": 100,
          "display_name_cn": "Adapter3",
          "display_name_en": "Adapter3",
          "validation_rule": ""
       })

    if need_adapter5:
        input_json["%s.PrepareInput.adapter5" % workflow_name] = default_adapter_5
        workflow_note.append({
          "description_cn": "5端接头序列",
          "key": "%s.PrepareInput.adapter5" % workflow_name,
          "required": False,
          "value_from": "",
          "default": default_adapter_5,
          "map_key": "",
          "description_en": "Adapter5",
          "type": "String",
          "order": 101,
          "display_name_cn": "Adapter5",
          "display_name_en": "Adapter5",
          "validation_rule": ""
       })
    if prepare_config.get("lookup_definition"):
        input_json["%s.PrepareInput.lookup_values" % workflow_name] = "$LookupValues$"

    with open(os.path.join(wdl_path, workflow_name + ".input.json"), 'w') as fh:
        fh.write(json.dumps(input_json, indent=3))
    params, input_files = remove_dup(workflow_note, input_files)
    with open(os.path.join(wdl_path, workflow_name + ".note.json"), 'w', encoding='UTF-8') as fh:
        fh.write(json.dumps({"parameters": params, "input_files": input_files, "lookup_definition": prepare_config.get("lookup_definition")}, indent=3, ensure_ascii=False))

    with open(os.path.join(wdl_path, workflow_name + ".rule.json"), 'w', encoding='UTF-8') as fh:
        fh.write(json.dumps(rules, indent=3, ensure_ascii=False))

    with open(os.path.join(sys.path[0], workflow_name, "app.conf"), 'w') as fh:
        fh.write("code=%s\nname=%s" % (workflow_code, workflow_name))
        if batch_analysis:
            fh.write("\nbatch_analysis=%s" % json.dumps(batch_analysis))

    bin_path = os.path.join(sys.path[0], workflow_name, "bin")
    if not os.path.exists(bin_path):
        os.makedirs(bin_path)
    copyfile(os.path.join(sys.path[0], "tools.py"), os.path.join(bin_path, "tools.py"))
    for file_name in os.listdir(os.path.join(sys.path[0], "common_python_packages")):
        path = os.path.join(sys.path[0], "common_python_packages", file_name)
        if os.path.isdir(path):
            try:
                copytree(path, os.path.join(bin_path, file_name))
            except:
                pass
        else:
            copyfile(path, os.path.join(bin_path, file_name))
    copyfile(os.path.join(sys.path[0], "tools.wdl"), os.path.join(wdl_path, "tools.wdl"))
    # set prepare task cpu and memery
    if prepare_config.get("capture_data") or prepare_config.get("lookup_definition"):
        template = """
        task PrepareInput
{
  input {
    String tools_main
    Array[Array[String]] data
    %(input)s
    String param_json
    String? adapter3
    String? adapter5
    String? parameter
  }
  %(capture)s
  command {
    python3 ${tools_main} prepare ${write_tsv(data)} ${param_json} %(param)s ${"--adapter3 " + adapter3} ${"--adapter5 " + adapter5} ${parameter}
  }

  output {
    Map[String, String] param = read_json(param_json)
  }
}
        """
        replace = {
            "input": "",
            "capture": "",
            "param": ""
        }
        if prepare_config.get("capture_data"):
            replace["capture"] = "runtime\n{\ncpu: \"4\"\nmemory: \"50 GB\"\n}\n"
        if prepare_config.get("lookup_definition"):
            replace["input"] = "Array[Object] lookup_values"
            replace["param"] = "--lookup-values ${write_objects(lookup_values)}"
        find = False
        with open(os.path.join(sys.path[0], "tools.wdl"), 'r') as fh:
            with open(os.path.join(wdl_path, "tools.wdl"), 'w') as f:
                for line in fh.readlines():
                    if line.strip().startswith("task PrepareInput"):
                        find = True
                    if find and line.startswith("}"):
                        f.write(template % replace)
                        find = False
                        continue
                    if not find:
                        f.write(line)

    with open(os.path.join(bin_path, "config.json"), 'w', encoding='UTF-8') as fh:
        fh.write(json.dumps(prepare_config, indent=3, ensure_ascii=False))

    lib_path = os.path.join(sys.path[0], workflow_name, "lib")
    if not os.path.exists(lib_path):
        os.makedirs(lib_path)
    with open(os.path.join(lib_path, 'readme.txt'), 'w') as fh:
        fh.write("this is read me.")

    resource_path = os.path.join(sys.path[0], workflow_name, "resource")
    if not os.path.exists(resource_path):
        os.makedirs(resource_path)
    with open(os.path.join(resource_path, 'readme.txt'), 'w') as fh:
        fh.write("this is read me.")

    with open(os.path.join(wdl_path, "tasks.json"), 'w', encoding='UTF-8') as fh:
        fh.write(json.dumps(workflow_tasks, indent=3, ensure_ascii=False))

    with open(os.path.join(wdl_path, "workflow.json"), 'w', encoding='UTF-8') as fh:
        fh.write(json.dumps(workflow, indent=3, ensure_ascii=False))


def create_task_wdl(step, tasks, workflow_name, task_file):
    task_id = step.get("task_id")
    mapping_task = None
    for task in tasks:
        if task.get("task_id") == task_id:
            mapping_task = task
            break
    if mapping_task:
        task_detail = decode_task(task, workflow_name)
        with open(task_file, 'w') as fh:
            fh.write(task_detail['wdl'])
        return task_detail, task
    else:
        raise Exception("Error: task_id:%s is not defined" % task_id)


def decode_task(task, workflow_name):
    global prepare_config
    input_files = task.get("input_files", [])
    prepare_config["input_files"].extend(input_files)
    main = task.get("main")
    cmd = task.get("cmd")
    task_id = task.get("task_id")
    wdl_string = ''
    rules = []
    input_json = {}
    task_input = ''
    task_output = ''
    task_command = ''
    workflow_call_input = 'main = "%s",\n' % main
    workflow_calculate = ''
    workflow_output = ''
    task_calculate = ''
    config_file_map = {}
    create_config_file_cmd = "python3 ${tools_main} create-conf-file write.tsv param.json"
    variants = {
        "sample.sample_id": "${sample_id}",
        "main": "${main}",
        "cpu": "${cpu}",
        "mem": "${mem}"
    }
    param_input_files_columns = []
    ## for parameters
    for param in task.get("parameters", []):
        calculate_line = ''
        param_type = param.get("type")
        default_value = param.get("default")
        required = param.get("required")
        value_from = param.get("value_from")
        key = param.get("key")
        map_key = param.get("map_key")
        variants["parameters.%s" % key] = "${%s}" % key
        param_just_string = False
        ## tools.py只能输出string的参数，并且会对数组的参数加以处理
        if param_type.startswith("Array") and re.search(r'\$\{sample\.metadata\.', value_from):
            param_type = "String"
            param_just_string = True
        ## sample.metadata remove to input_files
        if re.search(r'\$\{sample\.metadata\.', value_from) and not value_from.startswith("code#") and not param.get("no_need_to_note"):
            if param.get("look_up_map"):
                if not param.get("validation_rule"):
                    param["validation_rule"] = []
                    for item in param.get("look_up_map", []):
                        if item.get("display_en"):
                            param["validation_rule"].append(item.get("display_en"))
            param_input_files_columns.append(param)
        if param_type == "Boolean":
            param_name = "%s_parameter" % key
            cmd_line = "~{%s}" % param_name
            calculate_line = 'String %s = if %s then " %s " else ""' % (param_name, key, map_key)
            task_input_line = '%s? %s = %s' % (param_type, key, param.get("default", False))
        elif param_type.startswith("Array"):
            search_obj = re.search(r'Array\[([^\]]+)\]', param_type)
            if search_obj:
                sub_param_type = search_obj.groups()[0]
                task_input_line = '%s? %s' % (param_type, key)
                key_array = key
                if map_key:
                    key_array = "%s_array" % key
                    calculate_line = '%s %s = prefix("%s ", %s)' % (param_type, key_array, map_key, key)
                cmd_line = "${sep=\" \" %s}" % key_array
            else:
                raise Exception("Error: %s is not support param type" % param_type)
        elif param.get("have_blank_value") is True:
            param_name = "%s_parameter" % key
            calculate_line = '%s %s = if %s != "" then " %s \\"" + %s + "\\"" else ""' % (param_type, param_name, key, map_key, key)
            if param_just_string is True:
                calculate_line = '%s %s = if %s != "" then " %s " + %s else ""' % (
                param_type, param_name, key, map_key, key)
            cmd_line = "${%s}" % param_name
            task_input_line = '%s? %s=""' % (param_type, key)
        elif param.get('no_value_no_param') is True or (not required and (default_value is None or default_value == "")):
            # param_name = "%s_parameter" % key
            # calculate_line = '%s %s = if %s != "" then " %s " + %s else ""' % (param_type, param_name, key, map_key, key)
            cmd_line = "${\"%s \" + %s}" % (map_key, key)
            task_input_line = '%s? %s' % (param_type, key)
        else:
            cmd_line = '%s ${%s}' % (map_key, key)
            task_input_line = '%s %s' % (param_type, key)
        if not (default_value is None or default_value == ""):
            if param_type == "String" or param_type == "File":
                task_input_line = "%s %s = \"%s\"" % (param_type, key, default_value)
            else:
                task_input_line = "%s %s = %s" % (param_type, key, default_value)
            # if param_type == 'Int':
            if not value_from and not param.get("ui_no_need"):
                input_json["%s.%s.%s" % (workflow_name, task_id, key)] = default_value
        if key == 'parameter':
            task_input_line = ""
        if value_from:
            # param_key = value_from.split(".")[-1].replace('}', '')
            prepare_config["params"].append(param)
            if default_value:
                prepare_config["params"][-1]["default"] = default_value
            workflow_call_input += "%s = %s,\n" % (key, prepare_param % key)
            check_need_adapter(value_from)

        ## config file only need a param
        if param.get("config_filename") is not None:
            config_file_map[param.get("config_filename")] = map_key
            create_config_file_cmd = "%s --%s \"${%s}\"" % (create_config_file_cmd, key, key)
            cmd_line = None
            prepare_config["config_file_param"].append(param)

        task_calculate = '%s\n%s' % (task_calculate.strip(), calculate_line)
        if param.get("have_in_cmd") is not True:
            if cmd_line is not None:
                task_command = '%s\n%s \\' % (task_command, cmd_line)
        task_input = '%s\n%s' % (task_input, task_input_line)

    for config_file, map_key in config_file_map.items():
        # task_input = "%s\nFile %s" % (task_input, config_file.replace(".", "_").replace(" ", "_"))
        # workflow_call_input += "%s = %s,\n" % (config_file.replace(".", "_").replace(" ", "_"), prepare_param % config_file)
        task_command = '%s\n%s %s\\' % (task_command, map_key, config_file)

    for input_file in input_files:
        if input_file.get("no_need_create") is True:
            continue
        file_name = input_file.get("file_name")
        task_input = "%s\nFile %s" % (task_input, file_name)
        workflow_call_input += "%s = %s,\n" % (file_name, prepare_param % file_name)
        variants["input_files.%s" % file_name] = "${%s}" % file_name
        for column in input_file.get("columns", []):
            check_need_adapter(column.get("value_from"))
    #前端规则为，sample.metadata.*的数据在input_files里面查找，将parameter里面的sample.metadata.*转移到input_files里面
    if len(param_input_files_columns) > 0:
        input_files.append({
            "file_name": "params_file",
            "columns": param_input_files_columns,
            "no_need_create": True
        })
    create_log_cmds = []
    log_output = []
    for i, log in enumerate(task.get("logs", [])):
        log_path = prepare_expression(log) % variants
        log_name = os.path.basename(log_path)
        if log_name.startswith("*"):
            # megabolt log required
            log_name = log_name.replace("*", "sample_name")
        link_log_name = "BP_AUTO_LOGS_%s" % log_name
        create_log_cmds.append("ln -s -f %s %s" % (log_path, link_log_name))
        ends = link_log_name.split(".")[-1]
        log_output.append({
            "key": "BP_AUTO_LOGS_%s" % str(i+1),
            "value": log,
            "type": "File",
            "file_pattern": "logs/*.%s" % ends
        })

    output_raw_str = task.get("output_raw_str")
    if output_raw_str:
        output_path = task.get("output_path", "${outputdir}")
        rs, t_o, w_o = get_output_from_raw_str(output_raw_str, task_id, output_path)
        rules.extend(rs)
        task_output += t_o
        workflow_output += w_o
    outputs = remove_duplicate_file(task.get("outputs", []))
    log_output.extend(outputs)
    outputs = log_output
    for output in outputs:
        key = output.get("key")
        value = output.get("value")
        value = prepare_expression(value)
        output_type = output.get("type")
        if output_type == 'File' or output_type == 'Folder' or output_type == 'EachFolder':
            task_output += "File %s = \"%s\"\n" % (key, value)
            workflow_output += "File %s = %s.%s\n" % (key, task_id, key)
            ends = value.split(".")[-1]
            if output.get("no_need_archive") is not True:
                if output_type == 'File':
                    file_pattern = output.get("file_pattern", "[sampleid]/*.%s" % ends)
                    rules.append({
                        "type": key,
                        "subtype": "",
                        "file_pattern": file_pattern,
                        "wdl_output_key": key
                    })
                elif output_type == 'Folder':
                    rules.append({
                        "type": key,
                        "subtype": "",
                        "file_pattern": output.get("file_pattern", "[*]"),
                        "wdl_output_key": key
                    })
                else:
                    rules.append({
                        "type": key,
                        "subtype": "",
                        "file_pattern": output.get("file_pattern", "[each_sample_id]/[*]"),
                        "wdl_output_key": key
                    })
        elif output_type == 'String':
            task_output += "String %s = \"%s\"\n" % (key, value)
            workflow_output += "String %s = %s.%s\n" % (key, task_id, key)
        else:
            task_output += "%s %s = %s\n" % (output_type, key, value)
            workflow_output += "%s %s = %s.%s\n" % (output_type, key, task_id, key)

    cmd = prepare_expression(cmd)
    cmd = cmd % variants
    cmds = cmd.split("&&")
    tmp = cmds[-1].split(">")
    cmds[-1] = tmp[0]
    cmds[0] = "%s \%s" % (cmds[0], task_command.strip('\\'))
    task_command = " && ".join(cmds)
    if len(tmp) > 1:
        task_command = "%s > %s" % (task_command.strip('\\'), tmp[1])
    if len(create_log_cmds) > 0:
        task_command = "%s ; %s" % (";".join(create_log_cmds), task_command)
    if config_file_map:
        task_input = "%s\nString tools_main" % task_input
        workflow_call_input = "%stools_main   = tools_main,\n" % workflow_call_input
        task_command = "%s ;\n %s" % (create_config_file_cmd, task_command)
    if task_output.find("%(flowcell_id)s") != -1:
        variants.update({
            "flowcell_id": "${flowcell_id}",
            "lane_id": "${lane_id}",
            "barcode_id": "${barcode_id}"
        })
        flowcell_input = get_flowcell_input()
        task_input = "%s\n%s" %(task_input, flowcell_input["task_input"])
        workflow_call_input = "%s\n%s" %(workflow_call_input, flowcell_input["workflow_call_input"])
        workflow_calculate = "%s\n%s" %(workflow_calculate, flowcell_input["workflow_calculate"])
    task_output = task_output % variants

    wdl_template = get_task_wdl_template()
    task_cpu = task.get("cpu")
    cpu = task_cpu
    if type(task_cpu) == dict:
        cpu = task_cpu.get("default", 1)
        value_from = task_cpu.get("value_from")
        if value_from:
            prepare_config["params"].append({
                "key": "cpu",
                "value_from": value_from,
                "type": task_cpu.get("type", "String")
            })
            workflow_call_input += "cpu = %s,\n" % prepare_param % "cpu"
            check_need_adapter(value_from)
    task_memory = task.get("memory")
    memory = task_memory
    if type(task_memory) == dict:
        memory = task_memory.get("default", 1)
        value_from = task_memory.get("value_from")
        if value_from:
            prepare_config["params"].append({
                "key": "memory",
                "value_from": value_from,
                "type": task_memory.get("type", "String")
            })
            workflow_call_input += "mem = %s,\n" % prepare_param % "memory"
            check_need_adapter(value_from)
    wdl = wdl_template % {
        "task_id": task_id,
        "cpu": cpu,
        "memory": memory,
        "task_calculate": task_calculate.strip(),
        "task_output": task_output.strip(),
        "task_input": task_input.strip(),
        "task_command": task_command.strip(),
        "main": task.get("main")
    }

    # print(wdl)
    return {
            "input_json": input_json,
            "workflow_call_input": workflow_call_input,
            "wdl": wdl,
            "workflow_output": workflow_output,
            "parameters": task.get("parameters"),
            "rules": rules,
            "archive_rules": task.get("archive_rules", []),
            "get_qc_rules": task.get("get_qc_rules", []),
            "workflow_calculate": workflow_calculate,
            "input_files": input_files
    }


def get_output_from_raw_str(raw_str, task_name, output_path):
    total = 0
    all_origin_file = []
    all_wdl_file = []
    dup = {}
    rules = []
    task_output = ""
    workflow_output = ""
    for line in raw_str:
        if dup.get(line):
            continue
        else:
            dup[line] = ""
        line = line.replace("}", "").replace("{", "")
        find_obj = re.findall(r'\[.+?\]', line)

        origin_file = []
        wdl_file = []
        for i in find_obj:
            new_origin_file = []
            new_wdl_file = []
            for key in i.replace("[", "").replace("]", "").split("/"):
                if len(wdl_file) < 1:
                    if i == "[sampleid]":
                        new_wdl_file.append(line.replace("[sampleid]", "${sample_id}"))
                        new_origin_file.append(line)
                    else:
                        new_wdl_file.append(line.replace("%s" % i, key))
                        new_origin_file.append(line.replace("%s" % i, key))
                else:
                    for node in origin_file:
                        if i == "[sampleid]":
                            new_origin_file.append(node)
                        else:
                            new_origin_file.append(node.replace("%s" % i, key))
                    for node in wdl_file:
                        if i == "[sampleid]":
                            new_wdl_file.append(line.replace("[sampleid]", "${sample_id}"))
                        else:
                            new_wdl_file.append(node.replace("%s" % i, key))
            origin_file = new_origin_file
            wdl_file = new_wdl_file

        if len(find_obj) == 0:
            origin_file.append(line)
            wdl_file.append(line)
        all_origin_file.extend(origin_file)
        all_wdl_file.extend(wdl_file)
        total += len(wdl_file)
    check = {}
    for output in all_wdl_file:
        tmp = output.split(",")
        output = tmp[0]
        name = os.path.basename(output).replace("${sample_id}", "").replace("*", "").replace("-", "_").replace(".", "_").strip("_").replace("__", "_")
        o_name = None
        o_type = "File?"
        if len(tmp) > 1:
            o_name = tmp[1]
            o_type = "File"
        if re.search(r"^\d", name):
            name = "prefix_%s" % name
        if o_name:
            name = o_name
        name_num = check.get(name, 1)
        check[name] = name_num + 1
        if name_num != 1:
            name = name + "_" + str(name_num)
        # if check.get(name) and check.get(name) == output:
        #     continue
        # else:
        #     check[name] = output
        if re.search(r"\*", output):
            o_type = "Array[File?]"
            task_output += "%s %s = glob(\"%s/%s\")\n" % (o_type, name, output_path, output)
        else:
            task_output += "%s %s = \"%s/%s\"\n" % (o_type, name, output_path, output)
        workflow_output += "%s %s = %s.%s\n" % (o_type, name, task_name, name)
    check = {}
    check1 = {}
    for output in all_origin_file:
        tmp = output.split(",")
        output = tmp[0]
        name = os.path.basename(output).replace("[sampleid]", "").replace("*", "").replace("-", "_").replace(".", "_").strip("_").replace("__", "_")
        o_name = None
        if len(tmp) > 1:
            o_name = tmp[1]
        if o_name:
            name = o_name
        if re.search(r"^\d", name):
            name = "prefix_%s" % name
        name_num = check1.get(name, 1)
        check1[name] = name_num + 1
        if name_num != 1:
            name = name + "_" + str(name_num)
        # if check1.get(name) and check1.get(name) == output:
        #     continue
        # else:
        #     check1[name] = output
        count = check.get(name, 0)
        count += 1
        check[name] = count
        file_pattern = output
        file_pattern = file_pattern.replace("[sampleid]/", "", 1)
        pattern_path = os.path.dirname(file_pattern)
        tt = file_pattern.split("*")
        if len(tt) > 1:
            pattern_path = pattern_path.replace("*", "").replace("//", "/")
            if tt[-1].strip():
                file_pattern = os.path.join(pattern_path, "*%s" % tt[-1]).replace("\\", "/")
            else:
                file_pattern = os.path.join(pattern_path, "*").replace("\\", "/")
        rules.append({
          "file_pattern": file_pattern.replace('[sampleid]', '*'),
          "subtype": "",
          "wdl_output_key": name,
          "type": name
        })
        # print(origin_file)
    for k, v in check.items():
        if v > 1:
            print("Warmming:  dup ", k, v)
    return rules, task_output, workflow_output


def remove_duplicate_file(outputs):
    folders = []
    for output in outputs:
        if output.get("type") == "Folder" or output.get("type") == "EachFolder":
            folders.append(output)
    for folder in folders:
        for output in outputs:
            if output.get("key") != folder.get("key"):
                if output.get("value").find(folder.get("value")) != -1 and output.get("no_need_archive") is None:
                    output["no_need_archive"] = True
    return outputs


def get_task_wdl_template():
    return '''
version 1.0

task %(task_id)s
{
  input {
    %(task_input)s
    String main = "%(main)s"
    Int cpu = %(cpu)s
    Int mem = %(memory)s
    String sample_id
    String? parameter
  }

  %(task_calculate)s

  command {
    %(task_command)s
  }

  runtime {
    backend: "SGE"
    cpu: "${cpu}"
    memory: "${mem} GB"
  }

  output {
    %(task_output)s
  }
}
'''


def get_workflow_wdl_template():
    return '''
version 1.0
import "tools.wdl"
%(import_wdl)s

workflow %(workflow_id)s {
  input {
    Array[Array[String]] Data
    String SampleID
    %(inputs)s
  }

  ## SampleID = SampleName
  String sample_id = Data[0][0]
  String param_json = "param.json"
  String raw_fq1  = sub(Data[0][6], ",.*", "")
  String fq2  = sub(Data[0][6], ".*,", "")
  String raw_fq2 = if raw_fq1 == fq2 then "" else fq2
  %(calculate)s

  #program SECTION
  String Home  = "__INSTALL_PATH__/bin"
  String tools_main    = "${Home}/tools.py"

  call tools.PrepareInput {
    input:
    data                = Data,
    param_json          = param_json,
    tools_main          = tools_main,
  }

  %(call_tasks)s

  output {
    %(outputs)s
  }

  parameter_meta {
    SampleID : { description: "sample name with UID" }
    Data : {
      description: "data info: SAMPLE_ID\tSubprojectID\tProjectID\tLIB\tFLOWCELL\tLANE\tREAD1\tREAD2\tMETADATA_KEY\tMETADATA_VALUE"
    }
    Bundle : { description : "resource file" }
  }
}
'''


def prepare_expression(expression_str):
    for find_str in re.findall(r'\$\{[^\}]+\}', expression_str):
        expression_str = expression_str.replace(find_str, find_str.replace('$', '%').replace('{', '(').replace('}', ')') + 's')
    return expression_str


if __name__ == '__main__':
    global prepare_config, need_adapter3, need_adapter5
    if len(sys.argv) < 2:
        tasks = []
        workflows = []
        data_path = os.path.join(sys.path[0], 'data')
        for root, dirs, files in os.walk(data_path):
            for afile in files:
                json_file = os.path.join(root, afile)
                if json_file.endswith(".task.json"):
                    with open(json_file, 'r', encoding='UTF-8') as fh:
                        tasks.extend(json.loads(fh.read()))
                if json_file.endswith(".workflow.json"):
                    with open(json_file, 'r', encoding='UTF-8') as fh:
                        workflows.extend(json.loads(fh.read()))
        for workflow in workflows:
            prepare_config = {
                "input_files": [],
                "params": [],
                "archive_rules": [],
                "get_qc_rules": [],
                "config_file_param": [],
                "lookup_definition": []
            }
            need_adapter3 = False
            need_adapter5 = False
            decode_workflow(workflow, tasks)
    if len(sys.argv) > 2:
        task_file = sys.argv[1]
        workflow_file = sys.argv[2]
        with open(task_file, 'r', encoding='UTF-8') as fh:
            with open(workflow_file, 'r', encoding='UTF-8') as t:
                workflows = json.loads(t.read())
            tasks = json.loads(fh.read())
            for workflow in workflows:
                prepare_config = {
                    "input_files": [],
                    "params": [],
                    "archive_rules": [],
                    "get_qc_rules": [],
                    "config_file_param": [],
                    "lookup_definition": []
                }
                need_adapter3 = False
                need_adapter5 = False
                decode_workflow(workflow, tasks)
