using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using System.Diagnostics;
using System.Collections.Generic;

[assembly: System.Reflection.AssemblyTitle("AI Tool Launcher")]
[assembly: System.Reflection.AssemblyProduct("AI Tool Launcher")]

namespace LauncherWrapper {
    class Program {
        [DllImport("shell32.dll", SetLastError = true)]
        static extern void SetCurrentProcessExplicitAppUserModelID([MarshalAs(UnmanagedType.LPWStr)] string AppID);

        [STAThread]
        static void Main() {
            try { SetCurrentProcessExplicitAppUserModelID("ai.tool.launcher.2.0"); } catch {}

            string startDir = Application.StartupPath;
            string pyScript = "";

            // Check possible script locations
            string[] candidateScripts = new string[] {
                Path.Combine(startDir, "core", "launcher_v2.py"),
                Path.Combine(startDir, "2.0", "core", "launcher_v2.py"),
                Path.Combine(startDir, "core", "launcher.py"),
                Path.Combine(startDir, "1.0", "core", "launcher.py")
            };

            foreach (string s in candidateScripts) {
                if (File.Exists(s)) {
                    pyScript = s;
                    startDir = Path.GetDirectoryName(Path.GetDirectoryName(s));
                    break;
                }
            }

            if (string.IsNullOrEmpty(pyScript) || !File.Exists(pyScript)) {
                MessageBox.Show("找不到啟動器核心檔案 (launcher_v2.py)", "錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            // Find Python executable
            string pythonExe = FindPythonExecutable();
            if (string.IsNullOrEmpty(pythonExe) || !File.Exists(pythonExe)) {
                MessageBox.Show("找不到系統中的 Python 環境，請確認已安裝 Python 3.10+。", "錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = pythonExe;
            psi.Arguments = "\"" + pyScript + "\"";
            psi.WorkingDirectory = startDir;
            psi.UseShellExecute = false;
            psi.CreateNoWindow = true;

            try {
                Process.Start(psi);
            } catch (Exception ex) {
                MessageBox.Show("啟動失敗: " + ex.Message, "錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        static string FindPythonExecutable() {
            List<string> candidates = new List<string>();

            // 1. Common system paths
            candidates.Add(@"C:\Program Files\Python311\pythonw.exe");
            candidates.Add(@"C:\Program Files\Python311\python.exe");

            string userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);

            candidates.Add(Path.Combine(localAppData, @"Programs\Python\Python313\pythonw.exe"));
            candidates.Add(Path.Combine(localAppData, @"Programs\Python\Python312\pythonw.exe"));
            candidates.Add(Path.Combine(localAppData, @"Programs\Python\Python311\pythonw.exe"));
            candidates.Add(Path.Combine(localAppData, @"Programs\Python\Python310\pythonw.exe"));
            candidates.Add(Path.Combine(localAppData, @"Programs\Python\Python313\python.exe"));
            candidates.Add(Path.Combine(localAppData, @"Programs\Python\Python312\python.exe"));
            candidates.Add(Path.Combine(localAppData, @"Programs\Python\Python311\python.exe"));

            foreach (string path in candidates) {
                if (File.Exists(path)) return path;
            }

            // 2. Query where.exe
            try {
                Process p = new Process();
                p.StartInfo.FileName = "where.exe";
                p.StartInfo.Arguments = "pythonw";
                p.StartInfo.UseShellExecute = false;
                p.StartInfo.RedirectStandardOutput = true;
                p.StartInfo.CreateNoWindow = true;
                p.Start();
                string line = p.StandardOutput.ReadLine();
                p.WaitForExit();
                if (!string.IsNullOrEmpty(line) && File.Exists(line.Trim())) return line.Trim();
            } catch {}

            try {
                Process p = new Process();
                p.StartInfo.FileName = "where.exe";
                p.StartInfo.Arguments = "python";
                p.StartInfo.UseShellExecute = false;
                p.StartInfo.RedirectStandardOutput = true;
                p.StartInfo.CreateNoWindow = true;
                p.Start();
                string line = p.StandardOutput.ReadLine();
                p.WaitForExit();
                if (!string.IsNullOrEmpty(line) && File.Exists(line.Trim())) return line.Trim();
            } catch {}

            return "pythonw.exe";
        }
    }
}
