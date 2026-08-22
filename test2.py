import subprocess
import tempfile
import os

bat_path = os.path.join(tempfile.gettempdir(), "test2.bat")
with open(bat_path, "w") as f:
    f.write("echo hello > C:\\test_hello.txt\n")

p = subprocess.Popen([bat_path], creationflags=0x08000000)
p.wait()
