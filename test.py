import subprocess
p = subprocess.Popen(["cmd.exe", "/c", "start", '""', "/min", "C:\\test.bat"])
p.wait()
