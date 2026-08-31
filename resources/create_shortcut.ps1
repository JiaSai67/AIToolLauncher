$wshell = New-Object -ComObject WScript.Shell
$shortcut = $wshell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\AI Tool Launcher.lnk')
$shortcut.TargetPath = "C:\Users\chuan\AppData\Local\Programs\Python\Python313\pythonw.exe"
$shortcut.Arguments = "G:\python\toolLauncher\launcher.py"
$shortcut.WorkingDirectory = "G:\python\toolLauncher"
$shortcut.IconLocation = "G:\python\toolLauncher\icon.ico"
$shortcut.Save()
