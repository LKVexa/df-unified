using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text;

internal static class BootstrapRegression
{
    static int passed;
    static object Call(string name, params object[] args)
    {
        try { return typeof(Program).GetMethod(name, BindingFlags.Static | BindingFlags.NonPublic).Invoke(null, args); }
        catch (TargetInvocationException ex) { throw ex.InnerException; }
    }
    static void Check(bool ok, string name)
    {
        if (!ok) throw new Exception("FAIL " + name);
        passed++;
        Console.WriteLine("PASS " + name);
    }
    static byte[] Zip(string[] names, int size, bool link)
    {
        using (MemoryStream stream = new MemoryStream())
        {
            using (ZipArchive zip = new ZipArchive(stream, ZipArchiveMode.Create, true))
                foreach (string name in names)
                {
                    ZipArchiveEntry entry = zip.CreateEntry(name);
                    if (link) entry.ExternalAttributes = unchecked((int)0xA1FF0000);
                    using (Stream output = entry.Open()) output.Write(new byte[size], 0, size);
                }
            return stream.ToArray();
        }
    }
    static void Refuse(byte[] zip, string root, string name)
    {
        bool refused = false;
        try { Call("ExtractZipSafely", zip, root); }
        catch (InvalidDataException) { refused = true; }
        Check(refused, name);
        Check(!Directory.Exists(root) || Directory.GetFiles(root, "*", SearchOption.AllDirectories).Length == 0,
              name + " rejected before writing");
    }
    public static int Main()
    {
        string root = Path.Combine(Path.GetTempPath(), "df-unified-test-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try
        {
            string install = Path.Combine(root, "app");
            string marker = Path.Combine(root, "payload.sha256");
            byte[] valid = Zip(new string[] { "index.html", "assets/site.js" }, 8, false);
            Call("ExtractZipSafely", valid, install);
            File.WriteAllText(marker, "hash");
            string[] required = new string[] { "index.html", "assets/site.js" };
            Check((bool)Call("CacheIsValid", valid, install, marker, "hash", required), "valid cache");
            File.WriteAllBytes(Path.Combine(install, "assets/site.js"), Encoding.ASCII.GetBytes("tampered"));
            Check(!(bool)Call("CacheIsValid", valid, install, marker, "hash", required), "same-size cache tampering");
            File.WriteAllBytes(Path.Combine(install, "assets/site.js"), new byte[8]);
            File.WriteAllText(Path.Combine(install, "extra.js"), "extra");
            Check(!(bool)Call("CacheIsValid", valid, install, marker, "hash", required), "extra cache file");
            foreach (string name in new string[] { "../escape", "/absolute", "C:/drive", "name:ads", "NUL.txt", "a/../b", "a\\b", "trailing." })
                Refuse(Zip(new string[] { name }, 1, false), Path.Combine(root, "invalid"), name);
            Refuse(Zip(new string[] { "a", "A" }, 1, false), Path.Combine(root, "duplicate"), "case-insensitive duplicate");
            Refuse(Zip(new string[] { "link" }, 1, true), Path.Combine(root, "link"), "archive symlink");
            Refuse(Zip(new string[] { "oversize" }, 8 * 1024 * 1024 + 1, false), Path.Combine(root, "large"), "oversize archive entry");
            bool refused = false;
            try { Call("SafeDeleteDirectory", root, root); } catch (InvalidDataException) { refused = true; }
            Check(refused && Directory.Exists(root), "refuse deleting allowed root itself");
            Call("SafeDeleteDirectory", install, root);
            Check(!Directory.Exists(install), "bounded application subtree removal");
            Console.WriteLine("BOOTSTRAP_REGRESSIONS_PASS " + passed);
            return 0;
        }
        finally
        {
            // root is created above, fixed beneath TEMP, and contains only this harness's files.
            string temp = Path.GetFullPath(Path.GetTempPath()).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!Path.GetFullPath(root).StartsWith(temp, StringComparison.OrdinalIgnoreCase)) throw new Exception("Unsafe test cleanup");
            Call("SafeDeleteDirectory", root, Path.GetTempPath());
        }
    }
}
