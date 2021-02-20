# -*- coding: UTF-8 -*-
import logging
import requests
import time
import json
import sys
import os
import datetime
import re
import csv
import psutil
from requests.auth import HTTPBasicAuth

IDLE = "Idle"
RUNNING = "Running"
IS_RUNNING = "is_running"
IS_DONE = "is_done"
IS_TIME_OUT = "is_time_out"
CREATED = "created"
START = "start"
COMPLETE = "complete"
BGISEQ500 = "BGISEQ-500"
BGISEQ50 = "BGISEQ-50"

fh = open(os.path.join(sys.path[0], 'config.json'), 'r')
config = json.loads(fh.read())
fh.close()
logging_level = config.get("logging_level", "INFO")
hearbeat_interval = config.get("hearbeat_interval", 15)
check_status_interval = config.get("check_status_interval", hearbeat_interval * 8)
if logging_level == "INFO":
    logging_level = logging.INFO
elif logging_level == "ERROR":
    logging_level = logging.ERROR
else:
    logging_level = logging.INFO
log_file = "%s\\heartBeat.log" % os.environ['PUBLIC']
logging.basicConfig(
            filename=log_file,
            filemode='a',
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging_level)

def get_today_str():
    now = datetime.datetime.now()
    return '%04d%02d%02d' %(now.year, now.month, now.day)

def get_year():
    now = datetime.datetime.now()
    return now.year


class ZlimsTool():

    URLS = {
        'heartbeat': 'heartbeat/submit/',
        'resource_create': 'resources/instance/',
        'resource_update': 'resources/update/',
        'resource': 'resources/instance/'
    }

    def __init__(self):
        self.logger = logging.getLogger("ZLIMS")
        self.update_zlims_config()

    def update_zlims_config(self):
        fh = open(os.path.join(sys.path[0], 'config.json'), 'r')
        config = json.loads(fh.read())
        fh.close()
        self.API = 'http://%s:%s/zlims' % (config['HOST'], config['PORT'])
        self.AUTH = HTTPBasicAuth(config['USER'], config['PASSWORD'])
        logging_level = config.get("logging_level", "INFO")
        if logging_level == "INFO":
            logging_level = logging.INFO
        elif logging_level == "ERROR":
            logging_level = logging.ERROR
        else:
            logging_level = logging.INFO
        self.logger.setLevel(logging_level)


    def create_resource(self, part_number, serial_number, status='Idle'):
        payload = '''
        {
            "part_number": "%s",
            "serial_number": "%s",
            "metadata":{
                "instrument_status": "%s"
            }
        }
        ''' % (part_number, serial_number, status)
        r = self.callZlimsApi(ZlimsTool.URLS['resource_create'], "POST", payload, "createResource")
        return r


    def update_instrument_status(self, part_number, serial_number, status):
        query_url = "%s/?serial_number=%s" % (ZlimsTool.URLS['resource'], serial_number)
        r = self.callZlimsApi(query_url, "GET", {}, "getResource")
        if r is not False:
            if len(r) < 1:
                self.create_resource(part_number, serial_number)

            payload = '''
            [{
                "part_number": "%s",
                "serial_number": "%s",
                "metadata":{
                    "instrument_status": "%s"
                }
            }]
            ''' % (part_number, serial_number, status)
            r = self.callZlimsApi(ZlimsTool.URLS['resource_update'], "POST", payload, "updateResource")
        else:
            self.logger.error("Call ZLIMS API error.")

    def heartBeat(self, part_number, serial_number, instrument_status):
        payload = """
            {
                "part_number": "%s",
                "serial_number" : "%s",
                "send_alert_bool": true,
                "include_alert_details_bool": true,
                "inputs": {
                    "instrument_status": "%s"
                }
            }
        """ % (part_number, serial_number, instrument_status)
        logging.info("call zlims heart_beat")
        r = self.callZlimsApi(ZlimsTool.URLS['heartbeat'], "POST", payload, "submitHeartBeat")
        return r

    def callZlimsApi(self, url, method, payload={}, info=''):
        try:
            self.update_zlims_config()
            url = '%s/%s' % (self.API, url)
            headers = {'content-type': 'application/json'}
            response = requests.request(method, url, data=payload,
                                        headers=headers, auth=self.AUTH)
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
            logging.error("Url: " + url + "\n" + str(payload))
            msg = 'Call the ZLIMS (' + info + ') API Failed.' + str(e)
            logging.error(msg)
            return False


class SequencerMonitor():
    DB_FILE = os.path.join(sys.path[0], 'sequencer_monitor.db')

    def __init__(self, workpath, part_number):
        self.workpath = workpath
        self.part_number = part_number
        self.run_info = {}
        self.logger = logging.getLogger("Monitor")
        self.zlims_tools = ZlimsTool()
        self.serial_number = self.get_machine_name()
        self.software_dict = self.get_software_dict(part_number)
        self.zlims_tools.update_instrument_status(self.part_number, self.serial_number, IDLE)

    def save(self):
        with open(SequencerMonitor.DB_FILE, 'w') as f:
            json.dump(self.software_dict, f)

    def load_db(self):
        software_dict = {}
        if os.path.exists(SequencerMonitor.DB_FILE):
            try:
                with open(SequencerMonitor.DB_FILE, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warn("Can not read db file.")
        return software_dict

    def get_software_dict(self, part_number):
        software_dict = self.load_db()
        if software_dict:
            return software_dict
        else:
            if part_number == BGISEQ500:
                return {
                    "each_fov_max_time": 1.5 * 60 * 60,
                    "summary_report_max_time": 2 * 60 * 60,
                    "read1_to_read2_fov_max_time": 2.5 * 60 * 60,
                    "instrument_status": IDLE,
                    "sequencing_record": {}
                }
            if part_number == BGISEQ50:
                return {
                    'default_config': r'C:\\BGI\\Config\\BGI.ZebraV01Seq.Service.xml',
                    'start_sequencing_check': {
                        'file': 'C:\\BGI\\Logs\\BGI.ZebraV01Seq.Service-product-script-SE-{}.log',
                        'signal': 'BGI.ZebraV01Seq.Service',
                        'last_seek': os.SEEK_SET,
                        'last_seek_day': get_today_str()
                    },
                    'finish_sequencing_check': {
                        'file': 'C:\\BGI\\Logs\\BGI.ZebraV01Seq.Service-BaseCallClient-{}.log',
                        'signal': 'Write fastQ',
                        'last_seek': os.SEEK_SET,
                        'last_seek_day': get_today_str()
                    },
                    "instrument_status": IDLE
                }
            return {}

    def get_machine_name(self):
        return os.environ['COMPUTERNAME']

    def get_run_info(self, sequencing_path):
        run_info_file = os.path.join(sequencing_path, "RunInfo.csv")
        if os.path.exists(run_info_file):
            run_info = {}
            run_info['mtime'] = os.path.getmtime(run_info_file)
            basecall_path = "%s_result" % sequencing_path
            sequencing_folder_name = os.path.basename(sequencing_path)
            for line in csv.reader(open(run_info_file, 'r')):
                run_info[line[0].strip()] = line[1].strip()
            read1_len = int(run_info['Read1'])
            read2_len = int(run_info['Read2'])
            barcode_len = int(run_info['Barcode'])
            flowcell_id = run_info["Flowcell ID"]
            fov_check_points = []
            basecall_check_points = []
            circle = read1_len + read2_len + barcode_len
            ## init all basecall qc file

            for i in range(circle, 0, -1):
                fov_qc_file = "%s\\%s\\L02\\Intensities\\finInts\\S%.3d\\fovReport.QC.txt" %(basecall_path, flowcell_id, i)
                fov_check_points.append(fov_qc_file)
                fov_qc_file = "%s\\%s\\L01\\Intensities\\finInts\\S%.3d\\fovReport.QC.txt" %(basecall_path, flowcell_id, i)
                fov_check_points.append(fov_qc_file)
            ## get read1 last fov
            if read1_len != 0 and read2_len != 0:
                fov_file1 = "%s\\%s\\L01\\Intensities\\finInts\\S%.3d\\fovReport.QC.txt" %(basecall_path, flowcell_id, read1_len)
                fov_file2 = "%s\\%s\\L02\\Intensities\\finInts\\S%.3d\\fovReport.QC.txt" %(basecall_path, flowcell_id, read1_len)
                run_info["Read1_LAST_FOV_FILES"] = [fov_file1, fov_file2]
            else:
                run_info["Read1_LAST_FOV_FILES"] = []
            # summary report
            summary_report_file = "%s\\%s\\L01\\%s_%s_L01.summaryReport.html" %(basecall_path, flowcell_id, sequencing_folder_name, flowcell_id)
            basecall_check_points.append(summary_report_file)
            summary_report_file = "%s\\%s\\L02\\%s_%s_L02.summaryReport.html" %(basecall_path, flowcell_id, sequencing_folder_name, flowcell_id)
            basecall_check_points.append(summary_report_file)
            run_info['fov_check_points'] = fov_check_points
            run_info['basecall_check_points'] = basecall_check_points
            return run_info
        else:
            return False

    def analysis_log(self):
        latest_finish_date = self.check_signal_in_50_log(self.software_dict["finish_sequencing_check"])
        latest_start_date = self.check_signal_in_50_log(self.software_dict['start_sequencing_check'])
        if latest_start_date is not None:
            if latest_finish_date is None:
                self.logger.info('------------------Start sequencing------------------')
                self.software_dict['instrument_status'] = 'Running'
            else:
                if latest_start_date > latest_finish_date:
                    self.logger.info('------------------Start sequencing------------------')
                    self.software_dict['instrument_status'] = 'Running'
                else:
                    self.logger.info('------------------Finish sequencing------------------')
                    self.software_dict['instrument_status'] = 'Idle'
        elif latest_finish_date is not None:
            self.logger.info('------------------Finish sequencing------------------')
            self.software_dict['instrument_status'] = 'Idle'

    def check_signal_in_50_log(self, info):
        try:
            today = get_today_str()
            last_seek_day = info['last_seek_day']
            lass_seek = info['last_seek']
            signal = info.get('signal')
            if last_seek_day != today:
                lass_seek = os.SEEK_SET
            log_file = info['file'].format(today)
            fh = open(log_file, 'r')
            fh.seek(lass_seek)
            latest_signal_date = None
            for line in fh.readlines():
                if re.search(signal, line):
                    time_str = line.split(r'|')[0].strip().split('.')[0]
                    latest_signal_date = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
            info['last_seek'] = fh.tell()
            info['last_seek_day'] = today
            fh.close()
            if latest_signal_date:
                return latest_signal_date
        except Exception as e:
            self.logger.info(str(e))

    def call_heartbeat(self):
        instrument_status = self.software_dict["instrument_status"]
        self.zlims_tools.heartBeat(self.part_number, self.serial_number, instrument_status)

    def check_status(self):
        if self.part_number == BGISEQ50:
            self.logger.info("Start to check log file.")
            self.analysis_log()
        elif self.part_number == BGISEQ500:
            self.logger.info("Start to check sequencing file.")
            self.analysis_sequencing_path()
        else:
            self.logger.error("Sorry, not support %s" % self.part_number)

    def analysis_sequencing_path(self):
        sequencing_record = self.software_dict["sequencing_record"]
        each_fov_max_time = self.software_dict.get('each_fov_max_time')
        summary_report_max_time = self.software_dict.get('summary_report_max_time')
        read1_to_read2_fov_max_time = self.software_dict.get('read1_to_read2_fov_max_time')
        status_dict = sequencing_record.get("status_dict", {})
        pos_run_info = sequencing_record.get("pos_run_info", {})
        # update run info
        for item in os.listdir(self.workpath):
            if not item.endswith("_result"):
                if item not in status_dict.keys():
                    status_dict[item] = CREATED
                    sequencing_path = os.path.join(self.workpath, item)
                    run_info = self.get_run_info(sequencing_path)
                    if run_info:
                        run_info["status_dict_key"] = item
                        pattern = r'.+_(.)_%s' % run_info["Flowcell ID"]
                        search_obj = re.search(pattern, item)
                        if search_obj:
                            flowcell_pos = search_obj.group(1)
                            pos_info = pos_run_info.get(flowcell_pos, {})
                            last_mtime = pos_info.get("mtime", 0)
                            if run_info["mtime"] > last_mtime:
                                pos_run_info[flowcell_pos] = run_info
                        # only one flowcell like 50
                        else:
                            pass
                    else:
                        status_dict[item] = COMPLETE
        # check run status
        for flowcell_pos in pos_run_info.keys():
            run_info = pos_run_info[flowcell_pos]
            status_dict_key = run_info['status_dict_key']
            # if status_dict[status_dict_key] != COMPLETE:
            fov_check_points = run_info["fov_check_points"]
            basecall_check_points = run_info["basecall_check_points"]
            read1_last_fov_files = run_info["Read1_LAST_FOV_FILES"]

         ###  check summary report
            is_finish = True
            logging.info("====== Flowcell ID: %s, Flowcell Pos: %s ==========" %(run_info["Flowcell ID"], flowcell_pos))
            for summary_report_file in basecall_check_points:
                if not os.path.exists(summary_report_file):
                    is_finish = False
                    break
            if is_finish:
                logging.info('------------------Finish sequencing------------------')
                status_dict[status_dict_key] = COMPLETE
                continue
            else:
                fov_late_mtime = run_info.get('fov_late_mtime', None)
                if fov_late_mtime:
                    delta = time.time() - fov_late_mtime
                    if delta > summary_report_max_time:
                        logging.info('------------------Waiting summary report timeout, Basecall may be error. Set instrument to Idle------------------')
                        status_dict[status_dict_key] = COMPLETE

            ### check each fov
            status, fov_late_mtime = self.check_files_is_time_out(fov_check_points, read1_last_fov_files, each_fov_max_time, read1_to_read2_fov_max_time, run_info["mtime"])
            if status == IS_RUNNING:
                status_dict[status_dict_key] = START
            elif status == IS_DONE:
                run_info['fov_late_mtime'] = fov_late_mtime
            else:
                logging.info('------------------Fov file do not update, Sequencing may be error. Set instrument to Idle------------------')
                status_dict[status_dict_key] = COMPLETE

        # save all status to software_dict
        sequencing_record["status_dict"] = status_dict
        sequencing_record["pos_run_info"] = pos_run_info
        # update resource status
        for flowcell_pos in pos_run_info.keys():
            run_info = pos_run_info[flowcell_pos]
            status_dict_key = run_info['status_dict_key']
            if status_dict[status_dict_key] == START:
                self.software_dict["instrument_status"] = "Running"
                return
        self.software_dict["instrument_status"] = "Idle"
        return

    def check_files_is_time_out(self, qc_files, read1_last_fov_files, each_fov_max_time, read1_to_read2_fov_max_time, run_info_mtime):
        is_last_fov = True
        latest_fov_time = None
        ### check is first fov
        if time.time() - run_info_mtime < each_fov_max_time:
            return [IS_RUNNING, latest_fov_time]

        for qc_file in qc_files:
            if os.path.exists(qc_file):
                latest_fov_time = os.path.getmtime(qc_file)
                now = time.time()
                delta = now - latest_fov_time
                if is_last_fov:
                    return [IS_DONE, latest_fov_time]
                if qc_file in read1_last_fov_files and delta < read1_to_read2_fov_max_time:
                    return [IS_RUNNING, latest_fov_time]

                if delta > each_fov_max_time:
                    return [IS_TIME_OUT, latest_fov_time]
                else:
                    return [IS_RUNNING, latest_fov_time]
            is_last_fov = False
        return [IS_TIME_OUT, latest_fov_time]

    def run_check(self):
        count = 1
        while True:
            try:
                if count == 8:
                    count = 1
                    self.check_status()
                self.call_heartbeat()
            except Exception as e:
                self.logger.info(str(e))
            count += 1
            time.sleep(1)


def get_part_number():
    try:
        for pid in psutil.pids():
            p = psutil.Process(pid)
            if p.name() == 'BGI.ZebraV01Seq.Product.GUI.exe':
                return BGISEQ50
            if p.name() in ['MFCTest.exe', 'BGI Sequence Control Software.exe']:
                return BGISEQ500
    except:
        pass

if __name__ == '__main__':
    part_number = None
    logging.info("==== start deamon ====")
    while True:
        part_number = get_part_number()
        if part_number:
            break
        else:
            logging.info("Control software is not running!")
        time.sleep(5)

    count = 0
    monitor = SequencerMonitor("E:\SaveData", part_number)
    while True:
        try:
            monitor.call_heartbeat()
            if count >= check_status_interval:
                monitor.check_status()
                count = 0
                monitor.save()
        except Exception as e:
            logging.info(str(e))
        count += hearbeat_interval
        time.sleep(hearbeat_interval)
