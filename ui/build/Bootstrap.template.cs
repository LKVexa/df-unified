using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;
using System.Windows.Forms;

internal static class Program
{
    private const string Version = "__VERSION__";
    private const string ExpectedPayloadSha256 = "__PAYLOAD_SHA__";

    [STAThread]
    private static int Main(string[] args)
    {
        string logPath = null;
        try
        {
            string local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            if (String.IsNullOrWhiteSpace(local))
                throw new InvalidOperationException("LOCALAPPDATA is unavailable.");

            string logRoot = Path.Combine(local, "DF-VM-Technical-Institute", "logs");
            AssertNoLinks(logRoot);
            Directory.CreateDirectory(logRoot);
            logPath = Path.Combine(logRoot, "bootstrap-" + DateTime.Now.ToString("yyyyMMdd-HHmmss-fff") + ".log");
            Log(logPath, "Bootstrap v" + Version + " starting.");

            byte[] payload = DecodePayload();
            string actualHash = Sha256Hex(payload);
            Log(logPath, "Embedded payload SHA-256: " + actualHash);
            if (!String.Equals(actualHash, ExpectedPayloadSha256, StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("Embedded payload SHA-256 mismatch. Expected " + ExpectedPayloadSha256 + " but found " + actualHash + ".");

            string baseDir = Path.Combine(local, "DF-VM-Technical-Institute", Version);
            string installDir = Path.Combine(baseDir, "app");
            string marker = Path.Combine(baseDir, "payload.sha256");
            string[] required = new string[] {
                "index.html",
                Path.Combine("assets", "styles.css"),
                Path.Combine("assets", "data.js"),
                Path.Combine("assets", "site.js")
            };

            if (!CacheIsValid(payload, installDir, marker, actualHash, required))
            {
                Log(logPath, "Cache missing or stale; extracting embedded institute.");
                string stagingParent = Path.Combine(local, "DF-VM-Technical-Institute", ".staging-" + Version + "-" + Guid.NewGuid().ToString("N"));
                string stagingDir = Path.Combine(stagingParent, "app");
                AssertNoLinks(stagingDir);
                Directory.CreateDirectory(stagingDir);
                ExtractZipSafely(payload, stagingDir);
                ValidateRequired(stagingDir, required);

                SafeDeleteDirectory(installDir, Path.Combine(local, "DF-VM-Technical-Institute"));
                Directory.CreateDirectory(baseDir);
                Directory.Move(stagingDir, installDir);
                AssertNoLinks(marker);
                File.WriteAllText(marker, actualHash, Encoding.ASCII);
                SafeDeleteDirectory(stagingParent, Path.Combine(local, "DF-VM-Technical-Institute"));
                Log(logPath, "Installed validated payload to " + installDir);
            }
            else
            {
                Log(logPath, "Validated cached payload at " + installDir);
            }

            string index = Path.Combine(installDir, "index.html");
            bool fullscreen = HasArg(args, "--fullscreen");
            LaunchInstitute(index, fullscreen, logPath);
            Log(logPath, "Launch request completed.");
            return 0;
        }
        catch (Exception ex)
        {
            try { if (!String.IsNullOrEmpty(logPath)) Log(logPath, "ERROR " + ex.ToString()); } catch { }
            string message = "DF VM Technical Institute could not start.\r\n\r\n" + ex.Message;
            if (!String.IsNullOrEmpty(logPath)) message += "\r\n\r\nDiagnostic log:\r\n" + logPath;
            MessageBox.Show(message, "DF VM Technical Institute - Launch Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
    }

    private static byte[] DecodePayload()
    {
        string base64 = String.Concat(new string[] {
__BASE64_CHUNKS__
        });
        return Convert.FromBase64String(base64);
    }

    private const long MaxFileBytes = 8 * 1024 * 1024;
    private const long MaxTotalBytes = 64 * 1024 * 1024;

    private static void AssertNoLinks(string path)
    {
        for (string p = Path.GetFullPath(path); !String.IsNullOrEmpty(p); p = Path.GetDirectoryName(p))
        {
            try
            {
                if ((File.GetAttributes(p) & FileAttributes.ReparsePoint) != 0)
                    throw new InvalidDataException("Reparse points are not allowed: " + p);
            }
            catch (FileNotFoundException) { }
            catch (DirectoryNotFoundException) { }
        }
    }

    private static string EntryPath(string root, string name)
    {
        if (String.IsNullOrEmpty(name) || name.Length > 240 || name.Contains("\\") || name.StartsWith("/"))
            throw new InvalidDataException("Invalid archive path.");
        string clean = name.TrimEnd('/');
        foreach (string part in clean.Split('/'))
        {
            if (part.Length == 0 || part == "." || part == ".." || part.EndsWith(".") || part.EndsWith(" "))
                throw new InvalidDataException("Invalid archive component.");
            foreach (char c in part)
                if (!(Char.IsLetterOrDigit(c) && c < 128) && c != '-' && c != '_' && c != '.' && c != ' ')
                    throw new InvalidDataException("Unsupported archive character.");
            string stem = part.Split('.')[0].ToUpperInvariant();
            if (stem == "CON" || stem == "PRN" || stem == "AUX" || stem == "NUL" ||
                System.Text.RegularExpressions.Regex.IsMatch(stem, @"^(COM|LPT)[0-9]$"))
                throw new InvalidDataException("Reserved archive name.");
        }
        string fullRoot = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        string result = Path.GetFullPath(Path.Combine(fullRoot, clean.Replace('/', Path.DirectorySeparatorChar)));
        if (!result.StartsWith(fullRoot, StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Archive path escapes destination.");
        AssertNoLinks(result);
        return result;
    }

    private static List<ZipArchiveEntry> CheckedEntries(ZipArchive archive, string root)
    {
        if (archive.Entries.Count == 0 || archive.Entries.Count > 2048)
            throw new InvalidDataException("Invalid archive entry count.");
        long total = 0;
        HashSet<string> names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        List<ZipArchiveEntry> files = new List<ZipArchiveEntry>();
        foreach (ZipArchiveEntry entry in archive.Entries)
        {
            string path = EntryPath(root, entry.FullName);
            if (!names.Add(path)) throw new InvalidDataException("Duplicate archive path.");
            if (entry.Length < 0 || entry.Length > MaxFileBytes || total > MaxTotalBytes - entry.Length)
                throw new InvalidDataException("Archive exceeds size limit.");
            total += entry.Length;
            // ZIP external attributes may describe a Unix symlink or a Windows reparse point.
            if (((entry.ExternalAttributes >> 16) & 0xF000) == 0xA000 || (entry.ExternalAttributes & 0x400) != 0)
                throw new InvalidDataException("Archive links are not allowed.");
            if (entry.FullName.EndsWith("/"))
            {
                if (entry.Length != 0) throw new InvalidDataException("Nonempty directory entry.");
            }
            else files.Add(entry);
        }
        if (files.Count == 0) throw new InvalidDataException("Archive contains no files.");
        return files;
    }

    private static int CountFiles(string root)
    {
        AssertNoLinks(root);
        int count = 0;
        foreach (string item in Directory.GetFileSystemEntries(root))
        {
            AssertNoLinks(item);
            count += Directory.Exists(item) ? CountFiles(item) : 1;
            if (count > 2048) throw new InvalidDataException("Cache contains too many files.");
        }
        return count;
    }

    private static bool CacheIsValid(byte[] payload, string installDir, string marker, string expectedHash, string[] required)
    {
        AssertNoLinks(installDir);
        AssertNoLinks(marker);
        if (!Directory.Exists(installDir) || !File.Exists(marker)) return false;
        if (new FileInfo(marker).Length > 128 || File.ReadAllText(marker).Trim() != expectedHash) return false;
        using (MemoryStream ms = new MemoryStream(payload, false))
        using (ZipArchive archive = new ZipArchive(ms, ZipArchiveMode.Read, false))
        {
            List<ZipArchiveEntry> files = CheckedEntries(archive, installDir);
            if (CountFiles(installDir) != files.Count) return false;
            foreach (ZipArchiveEntry entry in files)
            {
                string path = EntryPath(installDir, entry.FullName);
                if (!File.Exists(path) || new FileInfo(path).Length != entry.Length) return false;
                using (Stream input = entry.Open())
                using (FileStream cached = File.OpenRead(path))
                using (SHA256 sha = SHA256.Create())
                    if (Convert.ToBase64String(sha.ComputeHash(input)) != Convert.ToBase64String(sha.ComputeHash(cached))) return false;
            }
        }
        ValidateRequired(installDir, required);
        return true;
    }

    private static void ValidateRequired(string root, string[] required)
    {
        foreach (string name in required)
            if (!File.Exists(EntryPath(root, name.Replace('\\', '/'))))
                throw new InvalidDataException("Payload missing required file: " + name);
    }

    private static void ExtractZipSafely(byte[] payload, string destination)
    {
        AssertNoLinks(destination);
        using (MemoryStream ms = new MemoryStream(payload, false))
        using (ZipArchive archive = new ZipArchive(ms, ZipArchiveMode.Read, false))
        {
            List<ZipArchiveEntry> files = CheckedEntries(archive, destination);
            foreach (ZipArchiveEntry entry in files)
            {
                string outPath = EntryPath(destination, entry.FullName);
                Directory.CreateDirectory(Path.GetDirectoryName(outPath));
                using (Stream input = entry.Open())
                using (FileStream output = new FileStream(outPath, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                {
                    byte[] buffer = new byte[8192];
                    long size = 0;
                    int n;
                    while ((n = input.Read(buffer, 0, buffer.Length)) != 0)
                    {
                        size += n;
                        if (size > entry.Length || size > MaxFileBytes) throw new InvalidDataException("Expanded size mismatch.");
                        output.Write(buffer, 0, n);
                    }
                    if (size != entry.Length) throw new InvalidDataException("Truncated archive member.");
                }
            }
        }
    }

    private static void LaunchInstitute(string indexPath, bool fullscreen, string logPath)
    {
        Uri indexUri = new Uri(indexPath);
        string browser = FindBrowser();
        if (!String.IsNullOrEmpty(browser))
        {
            string args = "--app=\"" + indexUri.AbsoluteUri + "\" --no-first-run --no-default-browser-check --disable-extensions " + (fullscreen ? "--start-fullscreen" : "--start-maximized");
            Log(logPath, "Starting browser: " + browser + " " + args);
            ProcessStartInfo psi = new ProcessStartInfo(browser, args);
            psi.UseShellExecute = false;
            Process.Start(psi);
            return;
        }

        Log(logPath, "No Edge/Chrome installation found; using Windows default file association.");
        ProcessStartInfo fallback = new ProcessStartInfo(indexPath);
        fallback.UseShellExecute = true;
        Process.Start(fallback);
    }

    private static string FindBrowser()
    {
        List<string> candidates = new List<string>();
        AddBrowserCandidate(candidates, Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), Path.Combine("Microsoft", "Edge", "Application", "msedge.exe"));
        AddBrowserCandidate(candidates, Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), Path.Combine("Microsoft", "Edge", "Application", "msedge.exe"));
        AddBrowserCandidate(candidates, Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), Path.Combine("Microsoft", "Edge", "Application", "msedge.exe"));
        AddBrowserCandidate(candidates, Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), Path.Combine("Google", "Chrome", "Application", "chrome.exe"));
        AddBrowserCandidate(candidates, Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), Path.Combine("Google", "Chrome", "Application", "chrome.exe"));
        AddBrowserCandidate(candidates, Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), Path.Combine("Google", "Chrome", "Application", "chrome.exe"));
        return candidates.Count > 0 ? candidates[0] : null;
    }

    private static void AddBrowserCandidate(List<string> list, string root, string relative)
    {
        if (String.IsNullOrWhiteSpace(root)) return;
        string p = Path.Combine(root, relative);
        if (File.Exists(p) && !list.Contains(p)) list.Add(p);
    }

    private static bool HasArg(string[] args, string expected)
    {
        if (args == null) return false;
        for (int i = 0; i < args.Length; i++)
            if (String.Equals(args[i], expected, StringComparison.OrdinalIgnoreCase)) return true;
        return false;
    }

    private static string Sha256Hex(byte[] bytes)
    {
        using (SHA256 sha = SHA256.Create())
        {
            byte[] hash = sha.ComputeHash(bytes);
            StringBuilder sb = new StringBuilder(hash.Length * 2);
            for (int i = 0; i < hash.Length; i++) sb.Append(hash[i].ToString("x2"));
            return sb.ToString();
        }
    }

    private static void SafeDeleteDirectory(string path, string allowedRoot)
    {
        string root = Path.GetFullPath(allowedRoot).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
        string target = Path.GetFullPath(path);
        if (!target.StartsWith(root, StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Deletion target is outside the application directory.");
        AssertNoLinks(target);
        if (!Directory.Exists(target)) return;
        CountFiles(target); // Validate the entire tree before removing any item.
        foreach (string item in Directory.GetFileSystemEntries(target))
        {
            AssertNoLinks(item);
            if (Directory.Exists(item)) SafeDeleteDirectory(item, allowedRoot);
            else File.Delete(item);
        }
        Directory.Delete(target, false);
    }

    private static void Log(string path, string message)
    {
        File.AppendAllText(path, DateTime.Now.ToString("o") + " " + message + Environment.NewLine, Encoding.UTF8);
    }
}
