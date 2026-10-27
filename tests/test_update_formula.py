import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('UPDATER_SOURCE', ROOT / 'scripts/update-formula.py'))
spec = importlib.util.spec_from_file_location('updater', SOURCE)
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class UpdateFormulaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        (self.root / 'Formula').mkdir()
        self.formula = self.root / 'Formula/heyditto.rb'
        self.original = (ROOT / 'Formula/heyditto.rb').read_text()
        self.formula.write_text(self.original)
        self.commit = 'a' * 40
        self.package = {'name': '@heyditto/cli', 'version': '2.33.0', 'license': 'MIT',
                        'bin': {'heyditto': 'dist/cli.js'}, 'engines': {'node': '^24.22.1'},
                        'dependencies': {'example': '1.0.0'}}
        self.metadata = {'name': '@heyditto/cli', 'version': '2.33.0', 'gitHead': self.commit,
                         'dist': {'tarball': 'https://registry.npmjs.org/@heyditto/cli/-/cli-2.33.0.tgz'}}
        self.lock = {'packages': {'': dict(self.package)}}

    def run_update(self, bad_integrity=False, tag=None):
        data = json.dumps(self.package).encode()
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode='w:gz') as tar:
            info = tarfile.TarInfo('package/package.json')
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        blob = archive.getvalue()
        self.metadata['dist']['integrity'] = 'sha512-' + base64.b64encode(hashlib.sha512(blob).digest()).decode()
        if bad_integrity:
            self.metadata['dist']['integrity'] = 'sha512-invalid'

        def fetch(url):
            if url.endswith('/2.33.0'):
                return json.dumps(self.metadata).encode()
            if url.endswith('.tgz'):
                return blob
            if url.endswith('/package-lock.json'):
                return json.dumps(self.lock).encode()
            raise RuntimeError('unexpected URL: ' + url)

        with patch.object(updater, '__file__', str(self.root / 'scripts/update-formula.py')), \
             patch.object(sys, 'argv', ['update-formula.py', '2.33.0']), \
             patch.object(updater, 'fetch', side_effect=fetch), \
             patch.object(updater, 'release_commit', return_value=tag or self.commit, create=True), \
             patch('sys.stdout', new_callable=io.StringIO):
            updater.main()

    def test_valid_update_keeps_both_node_literals(self):
        self.run_update()
        updated = self.formula.read_text()
        self.assertEqual(updated.count('24.22.1'), 2)
        self.assertIn(self.commit + '/package-lock.json', updated)

    def test_reject_bad_integrity(self):
        with self.assertRaisesRegex(ValueError, 'integrity mismatch'):
            self.run_update(bad_integrity=True)
        self.assertEqual(self.formula.read_text(), self.original)

    def test_reject_tag_mismatch(self):
        with self.assertRaisesRegex(ValueError, 'release tag'):
            self.run_update(tag='b' * 40)
        self.assertEqual(self.formula.read_text(), self.original)

    def test_reject_source_lock_mismatch(self):
        self.lock['packages']['']['dependencies'] = {'example': '9.0.0'}
        with self.assertRaisesRegex(ValueError, 'source lock mismatch'):
            self.run_update()
        self.assertEqual(self.formula.read_text(), self.original)

    def test_changed_node_convention_requires_manual_review(self):
        self.package['engines'] = {'node': '^24.22.1 <25'}
        with self.assertRaisesRegex(ValueError, 'review changed Node support manually'):
            self.run_update()
        self.assertEqual(self.formula.read_text(), self.original)

    def test_annotated_release_tag_uses_peeled_commit(self):
        tag = 'refs/tags/v2.33.0'
        result = subprocess.CompletedProcess([], 0, stdout=f"{'b'*40}\t{tag}\n{self.commit}\t{tag}^{{}}\n")
        with patch.object(updater.subprocess, 'run', return_value=result):
            self.assertEqual(updater.release_commit('2.33.0'), self.commit)


if __name__ == '__main__':
    unittest.main()
