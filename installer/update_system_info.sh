#!/bin/bash

#########################################################################################################
#
#				Variables
#
#########################################################################################################

# Version
version=1.0

# Configuration file
answer_file=/home/ztron/app_software/answer.json
installer=/home/ztron/app_software/installer.py

# main program

check_and_exit() {
  status=$?
  if [ "${status}" = "0" ]; then
    ::
  else
    zenity --info --title="Exiting..." --text="User canceled." --width=400 --height=250
    exit ${status}
  fi
}

sh /home/ztron/app_software/zlims-pro/init_product/select_products.sh 
company_code=$(zenity --entry --width=400 --height=250 --title="Update system infomation" --text="input company code:" )
check_and_exit
language=$(zenity --list --width=400 --height=250 --title="Update system infomation" --text="Select system language" --radiolist --column="Click	" --column="Options	" TRUE "zh_CN" FALSE "en_US")
check_and_exit
system_version=$(zenity --list --width=400 --height=250 --title="Update system infomation" --text="Select system version" --radiolist --column="Click	" --column="Options	" TRUE "lite" FALSE "ztron")
check_and_exit
echo "{\"ZLIMS_PRO_COMPANY_CODE\": \"${company_code}\", \"ZLIMS_PRO_LANGUAGE\": \"${language}\", \"ZLIMS_PRO_SYSTEM_VERSION\": \"${system_version}\"}" > ${answer_file}
chown ztron:ztron ${answer_file}
sudo su - ztron -c "python ${installer} config -a ${answer_file}"
status=$?
if [ "${status}" = "0" ]; then
  zenity --info --title="Exiting..." --text="Update succeed, company code: ${company_code}, language: ${language}, system_version: ${system_version}." --width=400 --height=250
else
  zenity --error --title="Error..." --text="Update failed, please try again." --width=400 --height=250
fi
