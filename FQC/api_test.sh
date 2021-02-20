test_path=/home/ztron/whole_unit_test
cd ${test_path}
ip=`cat config.py | grep ZLIMS_HOSTNAME | awk -F'"' '{print $2}'`
slanguage=`cat config.py | grep TEST_LANGUAGE | awk -F'"' '{print $2}'`

check_and_exit() {
  status=$?
  if [ "${status}" = "0" ]; then
    ::
  else
    zenity --info --title="Exiting..." --text="User canceled." --width=400 --height=250
    exit ${status}
  fi
}
ul=cn
if [ "${slanguage}" = "cn" ];then
  ul=en
fi

ip=$(zenity --entry --width=400 --height=250 --title="Input system infomation" --text="input zlims ip(default: ${ip}):")
check_and_exit
if [ "${ip}" != "" ];then
  sed -i "s/ZLIMS_HOSTNAME \?=.\+/ZLIMS_HOSTNAME = \"${ip}\"/" config.py
fi
language=$(zenity --list --width=400 --height=250 --title="Input system infomation" --text="Select system language" --radiolist --column="Click " --column="Options     " TRUE "${slanguage}" FALSE "${ul}")
check_and_exit
sed -i "s/TEST_LANGUAGE \?=.\+/TEST_LANGUAGE = \"${language}\"/" config.py
test_info=`sh run_test.sh`
zenity --info --title="Exiting..." --text="Test complete, please open *_PE_Unit_Test_Report.html to check test detail, test_info: ${test_info}." --width=400 --height=250
#sh run_test.sh | zenity --text-info --width=400 --height=250
firefox ./WGS_PE_Unit_Test_Report.html