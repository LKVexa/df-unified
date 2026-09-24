import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from df_unified import core


class UnifiedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = copy.deepcopy(core.UNIFIED)
        self.config['overlays'] = []
        for member in self.config['members']:
            path = self.root / member['container']
            for name, text in {'adapter/dfabric/cli.py': 'print("fixture delegation")\n',
                               'core/shared.py': 'VERSION = 1\n', 'VERIFY': 'verify', 'RUN': 'run'}.items():
                dest = path / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(text, encoding='utf-8')
            self.write(member['container'], 'reports/DF_CAPABILITY_LEDGER.json',
                       {'items': [{'id': str(i), 'title': token, 'statement': '',
                                   'status': 'BLOCKED_EXTERNAL_AUTHORITY'}
                                  for i, token in enumerate(core.PHYSICAL_OUTPUTS)]})
        for member in self.config['members']:
            if member['container'] != 'DF_Fabric':
                self.seal(member)
        self.write('DF_Fabric', 'fabric/NODES.json', {'nodes': [
            {'container': m['container'], 'sums_sha256': m['pins']['sums_sha256']}
            for m in self.config['members'] if m['container'] != 'DF_Fabric']})
        self.write('DF_Fabric', 'fabric/FEDERATION.json', {'network_policy': 'deny', 'backend_policy': 'none'})
        self.seal(next(m for m in self.config['members'] if m['container'] == 'DF_Fabric'))
        self.config_patch = patch.object(core, 'UNIFIED', self.config)
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)

    def write(self, member, rel, value):
        path = self.root / member / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    def seal(self, member):
        path = self.root / member['container']
        files = core.I.inventory(str(path))
        self.write(member['container'], 'MANIFEST.json',
                   {'files': files, 'file_count': len(files), 'inventory_exclusions': []})
        core.I.write_sums(str(path))
        member['pins'] = {'sums_sha256': core.sha256_file(path / 'SHA256SUMS.txt'),
                          'manifest_sha256': core.sha256_file(path / 'MANIFEST.json')}

    def members(self):
        return core.locate(str(self.root))[1]

    def gates(self, **kwargs):
        return {g['id']: g for g in core.battery(str(self.root), **kwargs)[2]}

    def test_valid_pinned_fixture(self):
        gates = self.gates()
        self.assertTrue(all(gates[f'U{i}']['status'] == 'PASS' for i in range(6)))
        self.assertEqual(gates['U6']['status'], 'SKIPPED')
        self.assertEqual(core.consolidated(self.members(), list(gates.values()))['verdict'], 'PASS')

    def test_missing_member_fails_without_native_execution(self):
        (self.root / 'DF_Small').rename(self.root / 'absent')
        with patch.object(core, 'delegate') as delegate:
            gates = self.gates(full=True)
        self.assertEqual(gates['U0']['status'], 'FAIL')
        self.assertEqual(gates['U6']['status'], 'SKIPPED')
        delegate.assert_not_called()

    def test_missing_entry_is_a_gate_failure(self):
        (self.root / 'DF_Small/MANIFEST.json').unlink()
        self.assertEqual(self.gates()['U1']['status'], 'FAIL')

    def test_same_size_tampering_fails_fast_status(self):
        (self.root / 'DF_Small/RUN').write_text('bad', encoding='utf-8')
        self.assertEqual(self.gates(deep=False)['U3']['status'], 'FAIL')

    def test_empty_shared_tree_refused(self):
        (self.root / 'DF_Small/core/shared.py').unlink()
        self.assertEqual(self.gates()['U2']['status'], 'FAIL')

    def test_missing_live_registry_refused(self):
        (self.root / 'DF_Fabric/fabric/NODES.json').unlink()
        self.assertEqual(self.gates()['U1']['status'], 'FAIL')

    def test_duplicate_live_node_refused(self):
        path = self.root / 'DF_Fabric/fabric/NODES.json'
        value = json.loads(path.read_text())
        value['nodes'][1] = value['nodes'][0]
        path.write_text(json.dumps(value))
        self.assertEqual(self.gates()['U1']['status'], 'FAIL')

    def test_missing_ledger_or_claim_refused(self):
        path = self.root / 'DF_Small/reports/DF_CAPABILITY_LEDGER.json'
        value = json.loads(path.read_text())
        value['items'].pop()
        path.write_text(json.dumps(value))
        self.assertEqual(self.gates()['U5']['status'], 'FAIL')
        path.unlink()
        self.assertEqual(self.gates()['U5']['status'], 'FAIL')

    def test_backend_policy_refused(self):
        self.write('DF_Fabric', 'fabric/FEDERATION.json', {'network_policy': 'deny', 'backend_policy': 'remote'})
        self.assertEqual(self.gates()['U5']['status'], 'FAIL')

    def test_missing_overlay_fails(self):
        self.config['overlays'] = [{'container': 'DF_Fabric', 'prefix': 'missing/', 'kind': 'test', 'status': 'BLOCKED'}]
        self.assertEqual(self.gates()['U4']['status'], 'FAIL')

    def test_file_overlay_does_not_authorize_prefix_sibling(self):
        self.assertTrue(core._overlay_matches('PHOTON.cmd', 'PHOTON.cmd'))
        self.assertFalse(core._overlay_matches('PHOTON.cmd.evil', 'PHOTON.cmd'))
        self.assertFalse(core._overlay_matches('pk-other/file', 'pk/'))

    def test_manifest_traversal_duplicate_and_invalid_size(self):
        member = self.members()[0]
        path = Path(member['path']) / 'MANIFEST.json'
        original = json.loads(path.read_text())
        for mutation in ('path', 'duplicate', 'size'):
            value = copy.deepcopy(original)
            if mutation == 'path': value['files'][0]['path'] = '../outside'
            if mutation == 'duplicate': value['files'].append(value['files'][0])
            if mutation == 'size': value['files'][0]['bytes'] = True
            path.write_text(json.dumps(value))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                core.inventory(member)

    def test_duplicate_json_rejected(self):
        path = self.root / 'DF_Small/MANIFEST.json'
        path.write_text('{"files":[],"files":[],"file_count":0}')
        self.assertEqual(self.gates()['U3']['status'], 'FAIL')

    def test_incomplete_checksum_inventory_refused(self):
        path = self.root / 'DF_Small/SHA256SUMS.txt'
        path.write_text('')
        self.assertEqual(self.gates()['U3']['status'], 'FAIL')

    def test_delegation_refuses_tampered_members(self):
        (self.root / 'DF_Small/RUN').write_text('bad')
        with patch.object(core.subprocess, 'run') as execute, self.assertRaises(ValueError):
            core.delegate(self.members()[0], 'node-verify', base=str(self.root))
        execute.assert_not_called()

    def test_delegation_uses_current_python_and_timeout(self):
        with patch.dict(os.environ, {'PYTHON': 'untrusted'}), patch.object(core.subprocess, 'run') as execute:
            execute.return_value.returncode = 0
            core.delegate(self.members()[0], 'node-verify', base=str(self.root))
        self.assertEqual(execute.call_args.args[0][0], sys.executable)
        self.assertEqual(execute.call_args.kwargs['timeout'], 1800)

    def test_incomplete_gate_set_never_passes(self):
        self.assertEqual(core.consolidated(self.members(), [])['verdict'], 'FAIL')

    def test_malformed_ledger_is_reported_without_crashing(self):
        path = self.root / 'DF_Small/reports/DF_CAPABILITY_LEDGER.json'
        for value in ([1], {'items': [None]}, {'items': [{'status': []}]}):
            path.write_text(json.dumps(value))
            gates = self.gates()
            self.assertEqual(gates['U5']['status'], 'FAIL')
            result = core.consolidated(self.members(), list(gates.values()))
            self.assertEqual(result['verdict'], 'FAIL')
            self.assertEqual(result['capability_items'], [])

    def test_registry_escape_refused(self):
        self.config['members'][0]['container'] = '../escape'
        with self.assertRaises(ValueError):
            core.locate(str(self.root))

    def test_report_link_refused(self):
        destination = self.root / 'outside'
        destination.write_text('unchanged')
        report = self.root / 'reports/UNIFIED_GATE_RESULTS.json'
        report.parent.mkdir()
        try:
            report.symlink_to(destination)
        except OSError:
            self.skipTest('filesystem links require OS privilege')
        with patch.object(core, 'HERE', str(self.root)), self.assertRaises(ValueError):
            core._atomic_text('reports/UNIFIED_GATE_RESULTS.json', 'overwrite')
        self.assertEqual(destination.read_text(), 'unchanged')

    def test_atomic_report_replacement(self):
        with patch.object(core, 'HERE', str(self.root)):
            core._atomic_text('reports/check.txt', 'first')
            core._atomic_text('reports/check.txt', 'second')
        self.assertEqual((self.root / 'reports/check.txt').read_text(), 'second')
        self.assertFalse(list((self.root / 'reports').glob('.df-report-*')))


if __name__ == '__main__':
    unittest.main()
