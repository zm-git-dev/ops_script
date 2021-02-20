#!/usr/bin/env python3
#coding:utf-8
###### Import Modules
import sys
import os
import re
import json
import glob
import requests
import time
PROG_VERSION = '0.0.1'
PROG_DATE = '2020-02-13'

###### Usage
USAGE = """

     Version %s  by Zxq  %s

     Usage: %s [prepare|archive] <tsv_file> <param_json> >STDOUT
""" % (PROG_VERSION, PROG_DATE, os.path.basename(sys.argv[0]))

READ1 = 'read1'
READ2 = 'read2'
METADATA_KEY = 'metadata_key'
METADATA_VALUE = 'metadata_value'
METADATA = 'metadata'
SAMPLE_ID = "sample_id"
FLOWCELL = 'flowcell_id'
LANE = 'lane_id'
BARCODE_ID = 'barcode_id'
COMMON_MAPPING = {
    SAMPLE_ID: 0,
    FLOWCELL: 4,
    LANE: 5,
    BARCODE_ID: 3,
    READ1: 6,
    READ2: 6,
    METADATA_KEY: 7,
    METADATA_VALUE: 8
}
adapter5 = ""
adapter3 = ""
METADATA_READ1 = "files.read1"
METADATA_READ2 = "files.read2"
ADAPTER5_VARIANT = "${adapter5}"


def prepare_expression(expression_str):
    for find_str in re.findall(r'\$\{[^\}]+\}', expression_str):
        expression_str = expression_str.replace(find_str, find_str.replace('$', '%').replace('{', '(').replace('}', ')') + 's')
    return expression_str


## only allow input parameters.output arriants
def parameter_output_to_output(expression_str, output):
    search_obj = re.search(r'(\$\{output\.[^\}]+\})', expression_str)
    if search_obj:
        expression_str = expression_str.replace(search_obj.groups()[0], output)
    return expression_str


def get_tsv_data(tsv_file, mappings=COMMON_MAPPING, validate_len=3, param_metadata=True, require_keys=[], seq="\t"):
    data = []
    sample_lines = {}
    with open(tsv_file, 'r') as fh:
        for line in fh.readlines():
            param_dict = {}
            miss_keys = require_keys#.copy()
            if not (line.startswith("#") or not line.strip()):
                line_array = line.strip().split(seq)
                sample_id = line_array[0]
                if len(line_array) < validate_len:
                    raise Exception("Error: tsv line colume should more than %s" % validate_len)
                for key, value in mappings.items():
                    if key == READ1:
                        if line_array[value]:
                            tmp = line_array[value].split(',')
                            param_dict[READ1] = [tmp[0]]
                            if len(tmp) > 1:
                                param_dict[READ2] = [tmp[1]]
                            else:
                                param_dict[READ2] = []
                        else:
                            param_dict[READ1] = []
                            param_dict[READ2] = []
                    elif key == METADATA_KEY and param_metadata:
                        try:
                            meta_keys = line_array[value].split(',')
                            meta_values = line_array[mappings[METADATA_VALUE]].split(',')
                        except:
                            meta_keys = []
                            meta_values = []
                        if len(meta_keys) != len(meta_values):
                            raise Exception("Error: number of metadata keys not equal number of metadata values")
                        metadata = {}
                        for mkey, mvalue in zip(meta_keys, meta_values):
                            if mkey in [METADATA_READ1, METADATA_READ2]:
                                metadata_read = metadata.get(mkey, [])
                                metadata_read.append(mvalue)
                                metadata[mkey] = metadata_read
                            else:
                                metadata[mkey] = mvalue
                            try:
                                miss_keys.remove(mkey)
                            except:
                                pass
                        param_dict[METADATA] = metadata
                    elif key == METADATA_VALUE or key == READ2:
                        pass
                    else:
                        param_dict[key] = line_array[value]
                if len(miss_keys) > 0:
                    raise Exception("Error: metadata miss keys(%s)" % ",".join(miss_keys))
                lines = sample_lines.get(sample_id, [])
                lines.append(param_dict)
                sample_lines[sample_id] = lines
        for sample_id, lines in sample_lines.items():
            final_line = lines.pop(0)
            for line in lines:
                final_line[READ1].extend(line[READ1])
                final_line[READ2].extend(line[READ2])
            data.append(final_line)
# metadata.read1, metadata.read2 > read1, read2
        for d in data:
            read1 = d.get(METADATA, {}).get(METADATA_READ1)
            if read1 and len(read1) > 0:
                d[READ1] = read1
            read2 = d.get(METADATA, {}).get(METADATA_READ2)
            if read2 and len(read2) > 0:
                d[READ2] = read2
    return data


def archive_result(tsv_file, output):
    configs = get_config()
    samples = get_tsv_data(tsv_file, COMMON_MAPPING, 7, True)
    for sample in samples:
        variants = get_sample_variants(sample)
        for rule in configs.get("archive_rules", []):
            if rule.get("codes"):
                origin_path = rule.get("origin_path")
                origin_path = parameter_output_to_output(origin_path, output)
                origin_path = prepare_expression(origin_path)
                origin_path = origin_path % variants
                variants["origin_path"] = origin_path
                codes = rule.get("codes")
                search_obj = re.search("(def\s+([^\(]+)\()", codes)
                if search_obj:
                    func_name = search_obj.groups()[1]
                    function_code = codes + "\nresult=%s()" % func_name
                    function_code = function_code.replace(search_obj.groups()[0], "def %s(samples=%s, sample=%s, origin_path='%s'" % (func_name, samples, sample, origin_path))
                    function_code = function_code % variants
                    results = {}
                    exec(function_code, results)
            else:
                origin_path = rule.get("origin_path")
                origin_path = parameter_output_to_output(origin_path, output)
                origin_path = prepare_expression(origin_path)
                origin_path = origin_path % variants
                target_path = rule.get("target_path")
                target_path = parameter_output_to_output(target_path, output)
                target_path = prepare_expression(target_path)
                target_path = target_path % variants
                operation = rule.get("operation", "mv")
                need_create_dir = target_path
                if os.path.isfile(origin_path):
                    need_create_dir = os.path.dirname(target_path)
                if not os.path.exists(need_create_dir):
                    os.makedirs(need_create_dir)
                cmd = "%s %s %s" % (operation, origin_path, target_path)
                if os.system(cmd) != 0:
                    raise Exception("Error: execute this command: %s" % cmd)


def get_qc_values(tsv_file, output, output_variants={}):
    configs = get_config()
    samples = get_tsv_data(tsv_file, COMMON_MAPPING, 7, True)
    qc_values = {}
    standards = {"NONE_NONE": "NONE"}
    for sample in samples:
        variants = get_sample_variants(sample)
        variants.update(output_variants)
        for rule in configs.get("get_qc_rules", []):
            key = rule.get("key")
            try:
                target_file = rule.get("target_file")
                target_file = parameter_output_to_output(target_file, output)
                target_file = prepare_expression(target_file)
                target_file = target_file % variants
                value_pattern = rule.get("value_pattern")
                standard_from = rule.get("standard_from")
                if standard_from:
                    standard = prepare_expression(standard_from)
                    standard = standard % variants
                    search_obj = re.search(r'([\->=< \d\.]+)', standard)
                    if search_obj:
                        standard = search_obj.groups()[0]
                    standards[key] = standard
                if value_pattern:
                    with open(target_file, 'r') as fh:
                        for line in fh.readlines():
                            search_obj = re.search(value_pattern, line)
                            if search_obj:
                                qc_values[key] = search_obj.groups()[0]
            except:
                pass

            if qc_values.get(key) is None and rule.get("required") is True:
                # be known None is not pass
                qc_values[key] = "None"
#                raise Exception("Error: qc values: %s is no find at result, analysis may be failed." % key)
#            if qc_values.get(key) is None:
#                qc_values[key] = ""
    return {
        "qc_values": qc_values,
        "standards": standards
    }

def update_flow(tsv_file, output):
    output_param = {}
    samples = get_tsv_data(tsv_file, COMMON_MAPPING, 7, True)
    metadata = samples[0][METADATA]
    company_num = metadata.get("company_num", "")
    workflow_code = metadata.get("workflow_code", "")
    if not company_num or not workflow_code:
        raise Exception("Field workflow_code or company_num is missing")
    consume_flow = 0
    residual_flow = 0
    res = get_flow_info()
    if not res:
        raise Exception("Call get_flow_info API failed!")
    usedFlow = res.get("allUsed", None)
    residualFlow = res.get("allLeft", None)
    if usedFlow == None or residualFlow == None:
        raise Exception("get_flow_info API result is not correct! %s"%res)
    else:
        usedFlow = int(usedFlow) / 1000000000000.0
        residualFlow = int(residualFlow) / 1000000000000.0
    r = update_license_table(workflow_code, company_num, residualFlow, usedFlow, samples[0][SAMPLE_ID])
    if not r:
        raise Exception("Call update_license_table API failed!")
    if r.get("retcode", 1) == 1:
        raise Exception("Residual flow is not enough!")
    output_param["usedFlow"] = str(usedFlow)
    output_param["residualFlow"]= str(residualFlow)
    return output_param

def get_flow_info():
    url = "http://127.0.0.1:8090/SystemManager/system/monitor/nodeFlow"
    n = 3
    try:
        while n:
            response = requests.request('GET', url, data={}, headers={'content-type': 'application/json'})
            if response.status_code >= 300:
                n -= 1
                if n == 0:
                    return False
                time.sleep(30)
            else:
                return json.loads(response.text)
    except Exception as e:
        raise Exception("Get flow info failed, error is %s"%e)

def update_license_table(workflow_code, company_num, residualFlow, usedFlow, sampleID):
    url = "http://127.0.0.1:8080/AutoRunLocal/application/update/licenseResidualFlow"
    payload = '''
    {
        "code":"%s",
        "companyNum": "%s",
        "residualFlow": %s,
        "usedFlow": %s,
        "sampleID": "%s"
    }
    '''%(workflow_code, company_num, residualFlow, usedFlow, sampleID)
    n = 3
    try:
        while n:
            response = requests.request('POST', url, data=payload, headers={'content-type': 'application/json'})
            if response.status_code >= 300:
                n -= 1
                if n == 0:
                    return False
                time.sleep(30)
            else:
                return json.loads(response.text)
    except Exception as e:
        raise Exception("Update license table failed, error is %s"%e)

def run_env_sh():
    env_sh = os.path.join(os.path.dirname(sys.argv[0]), "env.sh")
    if os.path.exists(env_sh):
        os.system("sh %s"%env_sh)

def get_config():
    with open(os.path.join(sys.path[0], "config.json"), 'r', encoding='utf-8') as fh:
        return json.loads(fh.read())


def prepare_inputs_for_common(tsv_file, lookup_values):
    ## tsv file: SAMPLE_ID\tSubprojectID\tProjectID\tLIB\tFLOWCELL\tLANE\tREAD1\tREAD2\tMetadata_keys\tMetadata_values
    samples = get_tsv_data(tsv_file, COMMON_MAPPING, 7, True)
    if samples is not None:
        samples[0]["LOOKUPVALUES"] = lookup_values
    configs = get_config()
    output_param = {}
    capture_data_config = configs.get("capture_data")
    capture_data(samples, capture_data_config)
    for input_file in configs.get("input_files", []):
        if input_file.get("no_need_create") is True:
            continue
        file_name = input_file.get("file_name")
        output_param[file_name] = os.path.realpath(file_name)
        barcode_files_type = input_file.get("barcode_files_type")
        barcode_files_merge_by = input_file.get("barcode_files_merge_by", ",")
        columns = []
        column_separator = input_file.get("column_separator", "\t")
        codes = input_file.get("codes", [])
        if len(codes) > 0:
            code_str = "\n".join(codes)
            search_obj = re.search(r'((def +(\S+)\()samples\))', code_str)
            if search_obj:
                new_str = search_obj.groups()[1] + "samples=%s)" % samples
                code_str = code_str.replace(search_obj.groups()[0], new_str) + ("\nresult=%s()" % search_obj.groups()[2])
                results = {}
                exec(code_str, results)
                lines = results.get("result")
                with open(file_name, 'w') as fh:
                    fh.write(lines)
        else:
            columns = input_file.get("columns", [])
            is_se = False if len(samples[0][READ2]) > 0 else True
            with open(file_name, 'w') as fh:
                for sample in samples:
                    variants = get_sample_variants(sample)
                    value_columns = []
                    if barcode_files_type == 'EACH_LINE':
                        read1s = variants["sample.metadata.%s" % METADATA_READ1]
                        read2s = variants["sample.metadata.%s" % METADATA_READ2]
                        for i, read1 in enumerate(read1s):
                            value_columns = []
                            variants["sample.metadata.%s" % METADATA_READ1] = read1
                            variants["sample.metadata.%s" % METADATA_READ2] = ""
                            if len(sample[READ2]) > 0:
                                variants["sample.metadata.%s" % METADATA_READ2] = sample[READ2][i]
                            for column in columns:
                                try:
                                    variant_value = prepare_expression(column.get("value_from")) % variants
                                    # 没有值且不是必填则不添加该列
                                    if (column.get("required") is False and not variant_value) or (is_se and column.get("value_from") == ADAPTER5_VARIANT):
                                        continue
                                    value_columns.append(variant_value)
                                except Exception as e:
                                    if column.get("default_value") is not None:
                                        value_columns.append(column.get("default_value"))
                                    elif column.get("required") is False:
                                        pass
                                    else:
                                        raise e
                            fh.write(column_separator.join(value_columns) + "\n")
                    elif barcode_files_type == "MERGE":
                        variants["sample.metadata.%s" % METADATA_READ1] = barcode_files_merge_by.join(variants["sample.metadata.%s" % METADATA_READ1])
                        variants["sample.metadata.%s" % METADATA_READ2] = barcode_files_merge_by.join(variants["sample.metadata.%s" % METADATA_READ2])
                        for column in columns:
                            try:
                                variant_value = prepare_expression(column.get("value_from")) % variants
                                # 没有值且不是必填则不添加该列
                                if (column.get("required") is False and not variant_value) or (is_se and column.get("value_from") == ADAPTER5_VARIANT):
                                    continue
                                value_columns.append(variant_value)
                            except Exception as e:
                                if column.get("default_value") is not None:
                                    value_columns.append(column.get("default_value"))
                                else:
                                    raise e
                        fh.write(column_separator.join(value_columns) + "\n")

    for param in configs.get("params", {}):
        key = param.get("key")
        variants = get_sample_variants(samples[0])
        variants["sample.metadata.%s" % METADATA_READ1] = samples[0][READ1]
        variants["sample.metadata.%s" % METADATA_READ2] = samples[0][READ2]
        variants["samples"] = samples
        value_from = prepare_expression(param.get("value_from", ""))
        if value_from.startswith("code#") and value_from.endswith("#"):
            search_obj = re.search("def\s+([^\(]+)\(", value_from)
            if search_obj:
                func_name = search_obj.groups()[0]
                function_code = value_from.replace("code#", '').strip("#") + "\nresult=%s()" % func_name
                function_code = function_code % variants
                results = {}
                exec(function_code, results)
                value = results.get("result")
                output_param[key] = get_lookup_value(value, param.get("look_up_map", []))
        else:
            fastq_volume = ""
            fastq_paths = []
            for fastq in samples[0][READ1]:
                fastq_path = os.path.dirname(fastq)
                if fastq_path not in fastq_paths:
                    fastq_paths.append(fastq_path)
                    fastq_volume += "-v %s:%s "%(fastq_path,fastq_path)
            variants["fastq_volume"] = fastq_volume
            variants["sample.metadata.%s" % METADATA_READ1] = ",".join(samples[0][READ1])
            variants["sample.metadata.%s" % METADATA_READ2] = ",".join(samples[0][READ2])
            try:
                value = value_from % variants
                output_param[key] = get_lookup_value(value, param.get("look_up_map", []))
            except:
                value = param.get("default", "")
                output_param[key] = get_lookup_value(value, param.get("look_up_map", []))
        if param.get("type") == "Int":
            try:
                output_param[key] = int(output_param[key])
            except:
                pass
        if type(output_param[key]) == list:
            try:
                map_key = " %s " % param.get("map_key", " ")
                output_param[key] = map_key.join(output_param[key])
            except:
                pass

    return output_param


def capture_data(samples, config):
    if config is None:
        return
    value_from = config.get("value_from")
    # if barcode data size is not balance, you should merge each barcode gz file, then cut data
    barcode_balance = config.get("barcode_balance", True)
    cmd_template = config.get("cmd")
    unit_map = {"K": 1000, "M": 1000 * 1000, "G": 1000*1000*1000, "P": 1000*1000*1000*1000}
    for sample in samples:
        variants = get_sample_variants(sample)
        try:
            value_from = prepare_expression(value_from)
            value = value_from % variants
            search_obj = re.search(r'^(\d+)(\w)?$', value)
            if search_obj:
                size, unit = search_obj.groups()
                ## lims input default is G
                unit = "G" if unit is None else unit
                if unit:
                    if unit_map.get(unit.upper()):
                        size = float(size) * unit_map.get(unit.upper())
                    else:
                        print("Data size unit from metadata not in [k, m, g, p], ignore capture data.")
                        return
                barcode_num = len(sample.get(READ1))
                read_len = get_read_len(sample.get(READ1)[0])
                if len(sample.get(READ2)) > 0:
                    barcode_num = barcode_num * 2
                read_num = int(size / barcode_num / read_len)
                new_read1s = []
                new_read2s = []
                all_cmd = []
                for new_reads, reads in zip([new_read1s, new_read2s], [sample.get(READ1, []), sample.get(READ2, [])]):
                    for read in reads:
                        output_fastq = os.path.realpath(os.path.basename(read))
                        variants = {
                            "input_fastq": read,
                            "read_num": read_num,
                            "output_fastq": output_fastq,
                        }
                        all_cmd.append(cmd_template % variants)
                        new_reads.append(output_fastq)
                print("\n".join(all_cmd))
                stat = os.system("\n".join(all_cmd))
                if stat == 0:
                    sample[READ1] = new_read1s
                    sample[READ2] = new_read2s
                else:
                    raise Exception("Error: execute seqtk error")
        except Exception as e:
            print("Can not get data size from metadata, ignore capture data.", e)


def get_read_len(read):
    cmd = "cat %s | head -2 | tail -1"
    if read.endswith(".gz"):
        cmd = "zcat %s | head -2 | tail -1"
    fh = os.popen(cmd % read, 'r')
    return len(fh.read().strip())


def get_lookup_value(input_key, look_up_map):
    for item in look_up_map:
        if item.get("display_cn") == input_key or item.get("display_en") == input_key:
            return item.get("value")
    return input_key


def get_sample_variants(sample):
    ## read1, read2 defualt from cvs column, can update from metadata
    variants = {
        "sample.%s" % SAMPLE_ID: sample[SAMPLE_ID],
        "adapter3": adapter3,
        "adapter5": adapter5,
        "sample.metadata.%s" % METADATA_READ1: sample[READ1],
        "sample.metadata.%s" % METADATA_READ2: sample[READ2],
        FLOWCELL: sample.get(FLOWCELL),
        LANE: sample.get(LANE),
        BARCODE_ID: sample.get(BARCODE_ID),
    }
    for key, value in sample[METADATA].items():
        variants["sample.metadata.%s" % key] = value
    return variants


def make_dir_for_file(afile):
    dir_name = os.path.dirname(afile)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name)


def add_param_from_config(ArgParser):
    configs = get_config()
    config_file_param = configs.get("config_file_param", [])
    for param in config_file_param:
        key = param.get("key")
        description = param.get("description")
        line_template = param.get("line_template", "%(key)s = %(value)s")
        ArgParser.add_argument("--%s" % key, action="store", dest=key, help=description)


def create_config_file(para):
    configs = get_config()
    config_file_param = configs.get("config_file_param", [])
    config_map = {}
    for param in config_file_param:
        key = param.get("key")
        config_filename = param.get("config_filename")
        lines = config_map.get(config_filename, [])
        value = ""
        try:
            value = getattr(para, key)
        except:
            pass
        value = "" if value is None else value
        line_template = param.get("line_template", "%(key)s = %(value)s")
        lines.append(line_template % {
            "key": key,
            "value": value
        })
        config_map[config_filename] = lines
    for filename, lines in config_map.items():
        with open(filename, 'w') as fh:
            fh.write("\n".join(lines))


def load_object_file(object_file):
    lookup_values = []
    with open(object_file, 'r') as fh:
        headers = fh.readline().strip().split("\t")
        for line in fh.readlines():
            contents = line.strip("\n").split("\t")
            data = {}
            for index, header in enumerate(headers):
                data[header] = contents[index]
            lookup_values.append(data)
    return lookup_values


def main():
    import argparse
    ArgParser = argparse.ArgumentParser(usage=USAGE)
    ArgParser.add_argument("--version", action="version", version=PROG_VERSION)
    ArgParser.add_argument("-c", "--config", action="store", dest="config", help="config file")
    ArgParser.add_argument("--result-dir", action="store", dest="result_dir", help="archive file origin path")
    ArgParser.add_argument("--adapter3", action="store", dest="adapter3", default="AAGTCGGAGGCCAAGCGGTCTTAGGAAGACAA", help="adapter3")
    ArgParser.add_argument("--adapter5", action="store", dest="adapter5", default="AAGTCGGATCGTAGCCATGTCGTTCTGTGAGCCAAGGAGTTG", help="adapter5")
    ArgParser.add_argument("--lookup-values", action="store", dest="lookup_values", help="look up values")
    add_param_from_config(ArgParser)
    (para, args) = ArgParser.parse_known_args()
    lookup_values = None
    if hasattr(para, "lookup_values") and para.lookup_values is not None:
        lookup_values = load_object_file(para.lookup_values)
    if len(args) < 3:
        ArgParser.print_help()
        print("\n[ERROR]: The parameters number is not correct!")
        sys.exit(1)
    (func, tsv_file, param_json) = args[:3]
    global adapter3, adapter5
    adapter3 = para.adapter3
    adapter5 = para.adapter5
    if func == 'prepare':
        run_env_sh()
        param = prepare_inputs_for_common(tsv_file, lookup_values)
        if not param:
            param = {}
        with open(param_json, 'w') as fh:
            fh.write(json.dumps(param))
    elif func == 'create-conf-file':
        create_config_file(para)
    elif func == 'archive':
        archive_result(tsv_file, para.result_dir)
    elif func == 'get-qc-values':
        output_variants = {}
        if os.path.exists(para.result_dir) and os.path.isfile(para.result_dir):
            with open(para.result_dir, 'r') as fh:
                for line in fh.readlines():
                    tmp = line.strip().split("\t")
                    output_variants[tmp[0]] = tmp[1]
        param = get_qc_values(tsv_file, para.result_dir, output_variants)
        if not param:
            param = {}
        with open(param_json, 'w') as fh:
            fh.write(json.dumps(param))
    elif func == 'update-flow':
        param = update_flow(tsv_file, para.result_dir)
        if not param:
            param = {}
        with open(param_json, 'w') as fh:
            fh.write(json.dumps(param))
    else:
        ArgParser.print_help()
        print("\n[ERROR]: The parameters number is not correct!")
        sys.exit(1)

    return 0


if __name__ == '__main__':
    return_code = main()
    sys.exit(return_code)
