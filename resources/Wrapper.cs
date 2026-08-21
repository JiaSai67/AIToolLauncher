using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using System.Diagnostics;
using System.Linq;

[assembly: System.Reflection.AssemblyTitle("AI Tool Launcher")]
[assembly: System.Reflection.AssemblyProduct("AI Tool Launcher")]

namespace LauncherWrapper {
    class Program {
        [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Auto)]
        public static extern IntPtr LoadLibrary(string dllToLoad);

        [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Ansi)]
        public static extern IntPtr GetProcAddress(IntPtr hModule, string procedureName);

        [DllImport("shell32.dll", SetLastError = true)]
        static extern void SetCurrentProcessExplicitAppUserModelID([MarshalAs(UnmanagedType.LPWStr)] string AppID);

        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        delegate void Py_Initialize();

        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        delegate int PyRun_SimpleString(string command);

        [STAThread]
        static void Main() {
            try { SetCurrentProcessExplicitAppUserModelID("ai.tool.launcher.1.0"); } catch {}

            string pyScript = Path.Combine(Application.StartupPath, "core", "launcher.py");
            if (!File.Exists(pyScript)) {
                MessageBox.Show("找不到核心檔案: core\\launcher.py", "錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            string sysPython = "";
            try {
                Process pSearch = new Process();
                pSearch.StartInfo.FileName = "where";
                pSearch.StartInfo.Arguments = "python"; 
                pSearch.StartInfo.UseShellExecute = false;
                pSearch.StartInfo.RedirectStandardOutput = true;
                pSearch.StartInfo.CreateNoWindow = true;
                pSearch.Start();
                sysPython = pSearch.StandardOutput.ReadLine();
                pSearch.WaitForExit();
            } catch {}

            string portablePython = Path.Combine(Application.StartupPath, "runtime", "python", "python.exe");
            string sourcePython = File.Exists(portablePython) ? portablePython : sysPython;

            if (string.IsNullOrEmpty(sourcePython) || !File.Exists(sourcePython)) {
                DialogResult res = MessageBox.Show(
                    "系統找不到 Python 環境！\n\n是否安裝 Python 3.11 ？\n預計大小 120 MB\n（將在背景完成安裝並開啟軟體）", 
                    "需要 Python 環境", MessageBoxButtons.YesNo, MessageBoxIcon.Information);
                if (res == DialogResult.Yes) {
                    try {
                        ProcessStartInfo instPsi = new ProcessStartInfo();
                        instPsi.FileName = "winget";
                        instPsi.Arguments = "install --id Python.Python.3.11 -e --accept-package-agreements --accept-source-agreements";
                        Process inst = Process.Start(instPsi);
                        inst.WaitForExit();
                        MessageBox.Show("安裝完成！\n請按確定後「再次點擊啟動器」。", "完畢", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    } catch (Exception ex) {
                        MessageBox.Show("安裝失敗: " + ex.Message, "錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    }
                }
                return;
            }

            string pythonDir = Path.GetDirectoryName(sourcePython);
            
            // Set paths for embedded Python
            Environment.SetEnvironmentVariable("PYTHONHOME", pythonDir);
            string newPath = pythonDir + ";" + Path.Combine(pythonDir, "DLLs") + ";" + Path.Combine(pythonDir, "Library", "bin") + ";" + Environment.GetEnvironmentVariable("PATH");
            Environment.SetEnvironmentVariable("PATH", newPath);
            Environment.SetEnvironmentVariable("TRUE_PYTHON_DIR", pythonDir);

            // Find python3*.dll
            string[] dlls = Directory.GetFiles(pythonDir, "python3*.dll");
            string pythonDll = dlls.FirstOrDefault(d => Path.GetFileName(d).Length == 13); // match python310.dll, python311.dll
            
            if (pythonDll == null) {
                SpawnProcessFallback(sourcePython, pyScript);
                return;
            }

            IntPtr pDll = LoadLibrary(pythonDll);
            if (pDll == IntPtr.Zero) {
                SpawnProcessFallback(sourcePython, pyScript);
                return;
            }

            IntPtr pInit = GetProcAddress(pDll, "Py_Initialize");
            IntPtr pRun = GetProcAddress(pDll, "PyRun_SimpleStringFlags");
            if (pRun == IntPtr.Zero) pRun = GetProcAddress(pDll, "PyRun_SimpleString");

            if (pInit == IntPtr.Zero || pRun == IntPtr.Zero) {
                SpawnProcessFallback(sourcePython, pyScript);
                return;
            }

            try {
                Py_Initialize init = (Py_Initialize)Marshal.GetDelegateForFunctionPointer(pInit, typeof(Py_Initialize));
                PyRun_SimpleString run = (PyRun_SimpleString)Marshal.GetDelegateForFunctionPointer(pRun, typeof(PyRun_SimpleString));

                init(); // Start python engine inside C# process!

                string pyCode = string.Format(@"
import sys
import os
sys.argv = [r'{0}']
os.environ['TRUE_PYTHON_DIR'] = r'{1}'
import runpy
runpy.run_path(r'{0}', run_name='__main__')
", pyScript, pythonDir);
                run(pyCode);
            } catch {
                SpawnProcessFallback(sourcePython, pyScript);
            }
        }

        static void SpawnProcessFallback(string sourcePython, string pyScript) {
            string pythonw = sourcePython.Replace("python.exe", "pythonw.exe");
            if (!File.Exists(pythonw)) pythonw = sourcePython;

            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = pythonw;
            psi.Arguments = "\"" + pyScript + "\"";
            psi.WorkingDirectory = Application.StartupPath;
            psi.UseShellExecute = false;
            Process.Start(psi);
        }
    }
}
