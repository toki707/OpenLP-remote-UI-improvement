/*
 * OpenLP - Open Source Lyrics Projection
 * Copyright (c) 2008-2024 OpenLP Developers
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Windows.Forms;

[assembly: AssemblyTitle("OpenLP Remote & PC UI Installer")]
[assembly: AssemblyDescription("Installe la nouvelle interface Mobile Remote et le Mode Simplifie PC pour OpenLP (GPLv3)")]
[assembly: AssemblyProduct("OpenLP UI Improvement")]
[assembly: AssemblyVersion("1.0.0.0")]

namespace OpenLPUISetup
{
    public class SetupForm : Form
    {
        private Label statusLabel;
        private Button installBtn;

        public SetupForm()
        {
            this.Text = "OpenLP — Installation Apple HIG & Liquid Glass (Mobile & PC)";
            this.Size = new Size(490, 275);
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(242, 242, 247);
            this.ForeColor = Color.FromArgb(29, 29, 31);
            this.Font = new Font("Segoe UI", 9.5F, FontStyle.Regular);

            Label titleLabel = new Label();
            titleLabel.Text = "OpenLP — Édition Apple HIG (Mobile & PC)";
            titleLabel.Font = new Font("Segoe UI", 13F, FontStyle.Bold);
            titleLabel.Location = new Point(24, 20);
            titleLabel.Size = new Size(430, 28);
            this.Controls.Add(titleLabel);

            Label descLabel = new Label();
            descLabel.Text = "Cet installateur met en place :\n" +
                             "• La Web Remote Apple HIG (barre pilule, Liquid Glass, iOS 18 & macOS)\n" +
                             "• Le thème Apple HIG (#F2F2F7 / #007AFF) et la barre Mode Simplifié sur PC\n" +
                             "• Les routes API v2 (Prévisualiseur, Galerie mobile, Bibles & Diapos)";
            descLabel.ForeColor = Color.FromArgb(110, 110, 115);
            descLabel.Location = new Point(24, 54);
            descLabel.Size = new Size(430, 80);
            this.Controls.Add(descLabel);

            statusLabel = new Label();
            statusLabel.Text = "Prêt à installer dans votre dossier utilisateur OpenLP.";
            statusLabel.ForeColor = Color.FromArgb(36, 138, 61);
            statusLabel.Location = new Point(24, 140);
            statusLabel.Size = new Size(430, 24);
            this.Controls.Add(statusLabel);

            installBtn = new Button();
            installBtn.Text = "Installer et Lancer OpenLP";
            installBtn.Font = new Font("Segoe UI", 10F, FontStyle.Bold);
            installBtn.BackColor = Color.FromArgb(0, 122, 255);
            installBtn.ForeColor = Color.White;
            installBtn.FlatStyle = FlatStyle.Flat;
            installBtn.FlatAppearance.BorderSize = 0;
            installBtn.Location = new Point(24, 174);
            installBtn.Size = new Size(260, 40);
            installBtn.Cursor = Cursors.Hand;
            installBtn.Click += OnInstallClick;
            this.Controls.Add(installBtn);

            Button closeBtn = new Button();
            closeBtn.Text = "Fermer";
            closeBtn.BackColor = Color.FromArgb(229, 229, 234);
            closeBtn.ForeColor = Color.FromArgb(29, 29, 31);
            closeBtn.FlatStyle = FlatStyle.Flat;
            closeBtn.FlatAppearance.BorderColor = Color.FromArgb(209, 209, 214);
            closeBtn.Location = new Point(296, 174);
            closeBtn.Size = new Size(140, 40);
            closeBtn.Cursor = Cursors.Hand;
            closeBtn.Click += (s, e) => this.Close();
            this.Controls.Add(closeBtn);
        }

        private void OnInstallClick(object sender, EventArgs e)
        {
            try
            {
                InstallFiles();
                statusLabel.Text = "Installation réussie ! Démarrage d'OpenLP...";
                string exePath = @"C:\Program Files\OpenLP\OpenLP.exe";
                if (File.Exists(exePath))
                {
                    foreach (var proc in Process.GetProcessesByName("OpenLP"))
                    {
                        try { proc.Kill(); proc.WaitForExit(3000); } catch { }
                    }
                    Process.Start(exePath);
                }
                MessageBox.Show(
                    "La nouvelle interface Mobile Remote et le Mode Simplifié PC ont été installés avec succès !",
                    "Installation terminée",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information
                );
            }
            catch (Exception ex)
            {
                MessageBox.Show("Erreur lors de l'installation : " + ex.Message, "Erreur", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        public static void InstallFiles()
        {
            string appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            string openlpData = Path.Combine(appData, "openlp", "data");
            string remotesDir = Path.Combine(openlpData, "remotes");
            string assetsDir = Path.Combine(remotesDir, "assets");
            string contribDir = Path.Combine(openlpData, "contrib", "plugins", "remote_enhancements");

            Directory.CreateDirectory(assetsDir);
            Directory.CreateDirectory(contribDir);

            ExtractResource("index.html", Path.Combine(remotesDir, "index.html"));
            ExtractResource("version.js", Path.Combine(assetsDir, "version.js"));
            ExtractResource("remoteenhancementsplugin.py", Path.Combine(contribDir, "remoteenhancementsplugin.py"));
        }

        private static void ExtractResource(string resourceName, string destinationPath)
        {
            Assembly asm = Assembly.GetExecutingAssembly();
            using (Stream stream = asm.GetManifestResourceStream(resourceName))
            {
                if (stream == null)
                    throw new FileNotFoundException("Ressource introuvable : " + resourceName);
                using (FileStream fs = new FileStream(destinationPath, FileMode.Create, FileAccess.Write))
                {
                    stream.CopyTo(fs);
                }
            }
        }

        [STAThread]
        public static void Main(string[] args)
        {
            if (args.Length > 0 && (args[0] == "/S" || args[0] == "--silent"))
            {
                InstallFiles();
                return;
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new SetupForm());
        }
    }
}
