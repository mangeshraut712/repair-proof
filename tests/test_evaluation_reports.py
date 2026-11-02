import subprocess
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class EvaluationReportTests(unittest.TestCase):
 def test_published_evaluation_reports_match_the_offline_evaluator(self):
  result=subprocess.run(
   [sys.executable,'scripts/verify_evaluations.py'],cwd=ROOT,
   capture_output=True,text=True,check=False,
  )
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertIn('Verified 2 evaluation reports.',result.stdout)
