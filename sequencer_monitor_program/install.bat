PowerShell.exe "set-executionpolicy remotesigned"
python -m pip install --no-index --find-links=C:\sequencer_monitor_program\packages -r C:\sequencer_monitor_program\requirement.txt
schtasks.exe /create /sc minute /mo 2 /tn "sequencer_monitor" /tr "PowerShell.exe -WindowStyle Hidden -file C:\sequencer_monitor_program\run_daemon.ps1"