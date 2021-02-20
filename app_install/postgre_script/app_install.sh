#!/bin/bash
UsaGe="Usage: $0 {install_path app_zip}"
if [  $# -ne 2 ]
 then
  echo $UsaGe  && exit 2
fi
DIR="$(cd "$(dirname "$0")" && pwd)"
app_install_path=$1
app_zip=$2
wdl_install_path=$app_install_path/WDL_Install
workflow_file=`less ${app_zip} | grep .workflow.wdl | awk '{print $NF}'| head -1`
app_name=`basename ${workflow_file} | sed -e 's/.workflow.wdl//'`
if [ -e "$app_install_path/${app_name}" ];then
    rm -fr $app_install_path/${app_name}
fi
mkdir -p $app_install_path
mkdir -p $wdl_install_path
cd $app_install_path
echo "unzip -o -P 123 $app_zip"
unzip -o -P 123 $app_zip

chmod 755 ${app_install_path}/${app_name}/bin/*

#2. 拷贝到固定目录
wdl_workflow=${app_install_path}/${workflow_file}
sed_str="s|__INSTALL_PATH__|${app_install_path}/${app_name}|g"
sed -i "$sed_str" $wdl_workflow
cd $DIR
echo "python3 $DIR/push_wdl.py $wdl_workflow $wdl_install_path"
nohup python3 $DIR/push_wdl.py $wdl_workflow $wdl_install_path 1>$DIR/push_wdl.o 2>$DIR/push_wdl.e
#cp $app_name/bin/* /home/zebracall/software/bin/
#----
#缺省
#lib
#resource
#----
