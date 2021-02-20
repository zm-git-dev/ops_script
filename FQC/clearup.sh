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
if zenity --question  --width=400 --height=250 --text "Warning data will not be restored after cleansing.\nDo you want to clean up system data?"; then
  python ${installer} clearup
  zenity --info --title="Exiting..." --text="Clean up succeed." --width=400 --height=250
else
  zenity --info --title="Exiting..." --text="Do nothing." --width=400 --height=250
fi
