import psutil
import logging
import requests
import time
import json
import sys
import os
from requests.auth import HTTPBasicAuth
from xml.dom.minidom import parse

log_file = "%s\\heartBeat.log" % os.environ['PUBLIC']

logging.basicConfig(
            filename=log_file,
            filemode='a',
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO)

SOFTWARE_50_DICT = {
    'default_config': r'C:\\BGI\\Config\\BGI.ZebraV01Seq.Service.xml',
    'main': 'BGI.ZebraV01Seq.Product.GUI.exe',
    'machine_type': 'bgiseq50'
}
SOFTWARE_500_DICT = {
    'default_config': r'C:\\Zebra\\BGI Sequence Control Software.exe.config',
    'main': 'BGI Sequence Control Software.exe',
    'machine_type': 'bgiseq500'
}


def submitHeartBeat(host, port, auth, payload):
    url = 'http://%s:%s/zlims/heartbeat/submit' % (host, port)
    r = callZlimsApi(url, "POST", auth, payload, "submitHeartBeat")
    return r

def callZlimsApi(url, method, auth, payload={}, info=''):
    try:
        headers = {'content-type': 'application/json'}
        response = requests.request(method, url, data=payload,
                                    headers=headers, auth=auth)
        if response.status_code >= 300:
            logging.error("Url: " + url + "\n" + payload)
            msg = ('Call the ZLIMS (' + info
                        + ') API Failed.  status code '
                        + str(response.status_code)
                        + "\n" + response.text)
            logging.error(msg)
            return False
        else:
            response.encoding = 'utf-8'
            return json.loads(response.text)
    except Exception as e:
        logging.error("Url: " + url + "\n" + payload)
        msg = 'Call the ZLIMS (' + info + ') API Failed.' + str(e)
        logging.error(msg)
        return False

def heartBeatDaemon(interval):
    while True:
        heartBeat()
        time.sleep(interval)

def heartBeat():
    try:
        software_dict, exe = isHardWareSoftOnline()
        if software_dict is not None:
            config = load_software_conf(software_dict['machine_type'], exe)
            zlims_host = config.get('BaseUrl')
            zlims_port = config.get('Port')
            zlims_user = config.get('UserName')
            zlims_password = config.get('Password')
            part_number = config.get('part_number', 'BGISEQ-50')
            serial_number = getInstrumentName()
            is_online_mode = config.get('IsOnlineMode')
            auth = HTTPBasicAuth(zlims_user, zlims_password)
            if zlims_host is not None and zlims_port is not None and (is_online_mode == 'True' or is_online_mode == 'true'):
                payload = """
                    {
                        "part_number": "%s",
                        "serial_number" : "%s",
                        "send_alert_bool": true,
                        "include_alert_details_bool": true,
                        "inputs": {}
                    }
                """ % (part_number, serial_number)
                logging.info("call zlims heart_beat")
                submitHeartBeat(zlims_host, zlims_port, auth, payload)
            else:
                logging.info("Config file set an offline mode!")
        else:
            logging.info("Control software is not running!")
    except Exception as e:
        logging.error(str(e))
        pass


def isHardWareSoftOnline():
    try:
        exe = ''
        for pid in psutil.pids():
            p = psutil.Process(pid)
            try:
                exe = p.exe()
            except:
                pass
            if p.name() == SOFTWARE_50_DICT['main']:
                return [SOFTWARE_50_DICT, exe]
            if p.name() == SOFTWARE_500_DICT['main']:
                return [SOFTWARE_500_DICT, exe]
    except:
        pass
    return [None, exe]

def getInstrumentName():
    return os.environ['COMPUTERNAME']

def getValueByTagName(ele, tag_name):
    elements = ele.getElementsByTagName(tag_name)
    if elements:
        if elements[0].childNodes:
            return elements[0].childNodes[0].data
        else:
            return None
    else:
        return None

def getParaNameDict(items):
    para_name_dict = {}
    for item in items:
        para_set_name = getValueByTagName(item, 'Para_Set_Name')
        if not para_name_dict.get(para_set_name):
            para_name_dict[para_set_name] = {}
        para_name = getValueByTagName(item, 'Para_Name')
        default_value = getValueByTagName(item, 'Def_Value')
        currrent_value = getValueByTagName(item, 'Cur_Value')
        instrument_name = getValueByTagName(item, 'Instrument_Name')
        if currrent_value:
            value = currrent_value
        else:
            value = default_value
        if para_name_dict.get(para_name):
            print(para_name + ' has dup value!')
        para_name_dict[para_set_name][para_name] = value
        para_name_dict[para_set_name]['Instrument_Name'] = instrument_name
    return para_name_dict

def get500ConfigDict(conf):
    para_name_dict = {}
    dom_tree = parse(conf)
    collection = dom_tree.documentElement
    application_ele = collection.getElementsByTagName('applicationSettings')[0]
    zlime_ele = application_ele.getElementsByTagName('BGI_Sequence_Control_Software.Properties.Settings')[0]
    setting_eles = zlime_ele.getElementsByTagName('setting')
    for ele in setting_eles:
        setting_name = ele.getAttribute('name')
        value = getValueByTagName(ele, 'value')
        if setting_name:
            if setting_name == 'LimsHost':
                para_name_dict['BaseUrl'] = value
            if setting_name == 'LimsHostPort':
                para_name_dict['Port'] = value
            if setting_name == 'LimsType':
                if value == 'zlims':
                    para_name_dict['IsOnlineMode'] = 'True'
                else:
                    para_name_dict['IsOnlineMode'] = 'False'
            if setting_name == 'HttpUser':
                para_name_dict['UserName'] = value
            if setting_name == 'Password':
                para_name_dict['Password'] = value
    return para_name_dict

def getConfigFileByMachine(machine_type, exe):
    if machine_type == 'bgiseq50':
        return SOFTWARE_50_DICT['default_config']
    if machine_type == 'bgiseq500':
        if exe:
            return exe + '.config'
        else:
            return SOFTWARE_500_DICT['default_config']

def load_software_conf(machine_type, exe):
    conf = getConfigFileByMachine(machine_type, exe)
    if machine_type == 'bgiseq50':
        dom_tree = parse(conf)
        collection = dom_tree.documentElement
        ii = collection.getElementsByTagName('InstrumentConfig')
        para_name_dict = getParaNameDict(ii)['ZLIMS']
        para_name_dict['part_number'] = "BGISEQ-50"
    else:
        para_name_dict = get500ConfigDict(conf)
        para_name_dict['part_number'] = "BGISEQ-500"
    return para_name_dict

def usage():
    msg = 'Usage: %s <bgiseq50|bgiseq500>\n' %sys.argv[0]
    logging.info(msg)
    sys.exit(0)

if __name__ == '__main__':

    logging.info('start heartbeat')
    heartBeatDaemon(15)