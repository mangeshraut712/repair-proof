import ast
import unittest

from repair_proof.fixtures import FIXTURES


class FixtureTests(unittest.TestCase):
    def test_balanced_registry(self):
        self.assertEqual(len(FIXTURES), 20)
        self.assertEqual(sum(f.category == 'repairable' for f in FIXTURES.values()), 12)
        self.assertEqual(sum(f.category == 'adversarial' for f in FIXTURES.values()), 8)
        self.assertEqual(sum(f.holdout for f in FIXTURES.values()), 4)
        for category in ('repairable', 'adversarial'):
            self.assertEqual(sum(f.holdout and f.category == category for f in FIXTURES.values()), 2)

    def test_authored_inputs_are_complete_and_syntactically_valid(self):
        for key, fixture in FIXTURES.items():
            with self.subTest(fixture=key):
                self.assertEqual(key, fixture.id)
                self.assertTrue(fixture.title)
                self.assertTrue(fixture.diagnosis)
                self.assertIn('AssertionError', fixture.log)
                self.assertIn('from solution import solve', fixture.test_source)
                self.assertNotEqual(fixture.source, fixture.replacement)
                ast.parse(fixture.source)
                ast.parse(fixture.replacement)
                ast.parse(fixture.test_source)

    def test_fixture_record_is_frozen(self):
        fixture = next(iter(FIXTURES.values()))
        with self.assertRaises(AttributeError):
            fixture.source = 'changed'

    def test_repairable_cases_are_distinct(self):
        cases = [f for f in FIXTURES.values() if f.category == 'repairable']
        self.assertEqual(len({f.source for f in cases}), 12)
        self.assertEqual(len({f.test_source for f in cases}), 12)


if __name__ == '__main__':
    unittest.main()
