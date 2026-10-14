import pathlib
import subprocess
import unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
class BootstrapTests(unittest.TestCase):
    def test_only_initial_install_question_is_accepted(self):
        script = ROOT/'scripts/bootstrap-bin/zenity'
        self.assertTrue(script.exists(), 'scoped installer confirmation missing')
        r = subprocess.run(['bash',str(script),'--question','--title=Steam installer'], capture_output=True)
        self.assertEqual(r.returncode,0)
    def test_other_dialogs_are_not_silenced(self):
        script = ROOT/'scripts/bootstrap-bin/zenity'
        self.assertTrue(script.exists(), 'scoped installer confirmation missing')
        self.assertIn('exec /usr/bin/zenity "$@"', script.read_text())
