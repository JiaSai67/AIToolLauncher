using System;
using System.IO;
using System.Diagnostics;

class T {
    static void Main() {
        string[] candidates = new string[] {
            @"C:\Program Files\Python311\pythonw.exe",
            @"C:\Program Files\Python311\python.exe"
        };
        foreach(var c in candidates) {
            Console.WriteLine(c + " exists: " + File.Exists(c));
        }
        string pyScript = @"G:\python\toolLauncher\2.0\core\launcher_v2.py";
        Console.WriteLine("Script: " + pyScript + " exists: " + File.Exists(pyScript));
        
        ProcessStartInfo psi = new ProcessStartInfo();
        psi.FileName = @"C:\Program Files\Python311\python.exe";
        psi.Arguments = "\"" + pyScript + "\"";
        psi.WorkingDirectory = @"G:\python\toolLauncher\2.0";
        psi.UseShellExecute = false;
        psi.RedirectStandardError = true;
        psi.RedirectStandardOutput = true;
        Process p = Process.Start(psi);
        p.WaitForExit(3000);
        Console.WriteLine("ExitCode: " + (p.HasExited ? p.ExitCode.ToString() : "STILL_RUNNING"));
        if (p.HasExited) {
            Console.WriteLine("STDOUT: " + p.StandardOutput.ReadToEnd());
            Console.WriteLine("STDERR: " + p.StandardError.ReadToEnd());
        }
    }
}
