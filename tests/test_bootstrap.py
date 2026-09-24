"""Compile and exercise extraction/cache helpers; never invoke the GUI entry point."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt', 'Windows .NET Framework bootstrap')
class BootstrapTests(unittest.TestCase):
    def test_archive_cache_and_deletion_regressions(self):
        compiler = Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        self.assertTrue(compiler.is_file(), 'Windows .NET Framework C# compiler is required')
        with tempfile.TemporaryDirectory(prefix='df-bootstrap-compile-') as directory:
            temp = Path(directory)
            source = (ROOT / 'ui/build/Bootstrap.template.cs').read_text(encoding='utf-8')
            source = source.replace('__VERSION__', 'test').replace('__PAYLOAD_SHA__', 'test').replace('__BASE64_CHUNKS__', '""')
            (temp / 'Program.cs').write_text(source, encoding='utf-8')
            exe = temp / 'regressions.exe'
            result = subprocess.run([str(compiler), '/nologo', '/target:exe', '/main:BootstrapRegression',
                '/out:' + str(exe), '/r:System.Windows.Forms.dll', '/r:System.IO.Compression.dll',
                '/r:System.IO.Compression.FileSystem.dll', str(temp / 'Program.cs'),
                str(ROOT / 'tests/BootstrapRegression.cs')], capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
            print(result.stdout)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('BOOTSTRAP_REGRESSIONS_PASS 27', result.stdout)


if __name__ == '__main__':
    unittest.main()
