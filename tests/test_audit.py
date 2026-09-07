import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from audit import evaluate, timestamp, main
class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.now=timestamp('2026-09-06T12:00:00Z')
        self.row=dict(service='App',owner='Team',rpo_hours='24',rto_hours='8',last_backup_utc='2026-09-06T06:00:00Z',last_restore_test_utc='2026-08-10T10:00:00Z',runbook_url='docs/recovery.md')
    def codes(self,**changes):
        return {f['code'] for f in evaluate(self.row|changes,self.now)['findings']}
    def test_complete_inventory(self): self.assertEqual(self.codes(),set())
    def test_exact_rpo_boundary(self): self.assertNotIn('BACKUP_EXCEEDS_RPO',self.codes(last_backup_utc='2026-09-05T12:00:00Z'))
    def test_one_second_beyond_rpo(self): self.assertIn('BACKUP_EXCEEDS_RPO',self.codes(last_backup_utc='2026-09-05T11:59:59Z'))
    def test_timezone_offset(self): self.assertEqual(self.codes(last_backup_utc='2026-09-06T01:00:00-05:00'),set())
    def test_naive_timestamp(self): self.assertIn('INVALID_LAST_BACKUP_UTC',self.codes(last_backup_utc='2026-09-06T06:00:00'))
    def test_future_timestamp(self): self.assertIn('FUTURE_LAST_BACKUP_UTC',self.codes(last_backup_utc='2026-09-07T00:00:00Z'))
    def test_invalid_targets(self):
        for value in ['NaN','inf','-2','0','']:
            self.assertIn('INVALID_RPO_HOURS',self.codes(rpo_hours=value))
    def test_overdue_restore(self): self.assertIn('RESTORE_TEST_OVERDUE',self.codes(last_restore_test_utc='2026-01-01T00:00:00Z'))
    def test_missing_owner_runbook(self): self.assertEqual(self.codes(owner='',runbook_url=''),{'MISSING_OWNER','MISSING_RUNBOOK'})
    def test_missing_backup(self): self.assertIn('MISSING_LAST_BACKUP_UTC',self.codes(last_backup_utc=''))
    def test_cli_json_and_exit_code(self):
        import json
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code=main(['examples/services.csv','--as-of','2026-09-06T12:00:00Z','--format','json'])
        report=json.loads(out.getvalue())
        self.assertEqual(code,1)
        self.assertEqual(report['service_count'],3)
        self.assertEqual(report['services_with_findings'],2)
    def test_bad_headers(self):
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/'bad.csv';file.write_text('service\nApp\n')
            with contextlib.redirect_stderr(io.StringIO()): self.assertEqual(main([str(file)]),2)
    def test_duplicate_service(self):
        from audit import audit
        with tempfile.TemporaryDirectory() as folder:
            file=Path(folder)/'duplicate.csv'
            lines=Path('examples/services.csv').read_text().splitlines()
            file.write_text('\n'.join([lines[0],lines[1],lines[1]])+'\n')
            with self.assertRaisesRegex(ValueError,'Duplicate'): audit(file,self.now,90)
if __name__=='__main__': unittest.main()
