BEGIN TRANSACTION;
INSERT INTO bp_auto.t_dl_rule (id, omics, workflow, type, subtype, file, thirdtype, extendtype, wdloutputkey)
VALUES (-1, 'genomics', 'upload_fastq', 'rawFastqFile', '', '[*]', null, null, 'upload_file_path');

INSERT INTO bp_auto.t_dl_product (code, wdl, platform, mail, "user", json, workflow, type, soname, sponame, afterjob, beforejob, spafterjob, spbeforejob, pbeforejob, pafterjob, isPublic, note, poname, extra, step, omics, prefix, taskzip, zone, batch_analysis, upload)
VALUES ('AP2020031602107314', '/home/ztron/app_software/wdl_script/get_flowcell_qc.py', 'SGE', 'ztron.genomics.cn', 'ztron', '/storeData/ztron/apps/WDL_Install/input_json/upload_fastq.input.json', 'upload_fastq', '', 'SimpleSingleSO', 'SimpleSingleSPO', '', 'SamplePassEvent', '', '', '', '', 0, '', 'SimpleSinglePO', '', 'UploadFastq', '', 'upload_fastq', '/storeData/ztron/apps/WDL_Install/tasks/upload_fastq.task.zip', 'sz', false, false);

INSERT INTO bp_auto.t_dl_template (filename, headers, prefix, notepath, check_columns, headers_chn, input_columns, project_column, subproject_column, validator_name, column_count, headersChn)
VALUES ('upload_fastq.txt', 'None', 'upload_fastq', '/storeData/ztron/apps/WDL_Install/notes/upload_fastq.note.json', '', 'None', '', 2, 1, 'BasicTemplateValidator', 0, null);

INSERT INTO bp_auto.t_dl_extra_user_config (configname, accounts, cal_paths, code, createtime, default_paths, handover_paths, isPublic, note, store_paths, store_time, username, updateTime, prefix, mailcode, zone)
VALUES ('Upload_Fastq', 'ztron', '-1', 'AP2020031602107314', '2020-07-29 18:22:31', '-1', '', 0, '', '', 30, 'ztron', '2020-07-29 18:22:31', 'upload_fastq', 0, 'sz');
END TRANSACTION;
