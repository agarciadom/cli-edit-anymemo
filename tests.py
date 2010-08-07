#!/usr/bin/python3.1
import add_terms
import io
import shutil
import sqlite3
import sys
import tempfile
import unittest

"""Unit tests for the add-terms.py script."""

# Path to the test database
TEST_DB = "test.db"


class TestAddTerms(unittest.TestCase):

    def setUp(self):
        self.testdb = tempfile.NamedTemporaryFile(delete=False)
        shutil.copyfileobj(open(TEST_DB, 'rb'), self.testdb.file)
        self.conn = sqlite3.connect(self.testdb.name)
        self.cursor = self.conn.cursor()

    def tearDown(self):
        del self.cursor
        self.conn.close()
        self.testdb.close()

    def run_program(self, argv=[], stdin=""):
        try:
            sys.stdin = io.StringIO(stdin)
            sys.stderr = io.StringIO()
            sys.stdout = io.StringIO()
            add_terms.main(["-d", self.testdb.name] + argv)
            self.str_stderr = sys.stderr.getvalue()
            self.str_stdout = sys.stdout.getvalue()
        finally:
            sys.stdin = sys.__stdin__
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

    def get_entries(self):
        self.cursor.execute(
            'SELECT _id, question, answer, category FROM dict_tbl')
        return self.cursor.fetchall()

    def testEmptyInput(self):
        """Tests that an empty input does not produce any changes in
        the BD."""
        original_rows = self.get_entries()
        self.run_program()
        final_rows = self.get_entries()
        self.assertIn("Saving", self.str_stderr)
        self.assertEquals(original_rows, final_rows,
                          "Empty input should not produce changes in the DB")

    def testRegularAddition(self):
        """Tests that simply adding a new entry with a new question, a
        new answer and an existing category works as expected, with no
        confirmation required."""
        new_row = (29, "hi", "ho", "French (Body parts)")
        self.run_program(stdin="\n".join(new_row[1:]))
        final_rows = self.get_entries()
        self.assertEquals(new_row, final_rows[-1])

    def testExistingQuestionConfirm(self):
        """Tests that the user is asked for confirmation if the
        question already exists, and that the entry is added if the
        user says 'y'."""
        self.run_program(stdin="toe\ny\nfoo\nFrench (Body parts)")
        final_rows = self.get_entries()
        self.assertIn("Proceed?", self.str_stdout)
        self.assertEquals((29, "toe", "foo", "French (Body parts)"),
                          final_rows[-1])

    def testExistingQuestionReject(self):
        """Tests that the user is asked for confirmation if the
        category does not exist yet, and that the entry is *not* added
        if the user says anything but 'y' or 'yes'."""
        self.run_program(stdin="toe\nn\nfoo\nFrench (Body parts)")
        final_rows = self.get_entries()
        self.assertIn("Proceed?", self.str_stdout)
        self.assertEquals(28, final_rows[-1][0])

    def baseTestExistingQuestionForce(self, argv=["-f"]):
        """Base function for the test cases involving -f and an
        existing question."""
        new_row = (29, "toe", "foo", "French (Body parts)")
        self.run_program(argv, stdin="\n".join(new_row[1:]))
        self.assertEquals(new_row, self.get_entries()[-1])

    def baseTestExistingQuestionSkip(self, argv=["-s"]):
        """Base function for the test cases involving -s and an
        existing question."""
        existing_question = "toe"
        new_row = (29, "foo", "bar", "French (Body parts)")
        self.run_program(
            argv=["-s"],
            stdin=existing_question + "\n" + "\n".join(new_row[1:]))
        self.assertEquals(new_row, self.get_entries()[-1])

    def testExistingQuestionForce(self):
        """Tests that the user is not asked for confirmation if -f is
        used, even if the question already exists. The entry should be
        added as is."""
        self.baseTestExistingQuestionForce()

    def testExistingQuestionForceOverridesSkip(self):
        """Tests that the user is not asked for confirmation if -f is
        used, even if the question already exists. The entry should be
        added as is. This version checks that -f overrides a previous
        -s."""
        self.baseTestExistingQuestionForce(argv=["-s", "-f"])

    def testExistingQuestionSkip(self):
        """Tests that the user is not asked for confirmation if -s is
        used and the question already exists. The entry should be
        skipped, and a new one will be read."""
        self.baseTestExistingQuestionSkip()

    def testExistingQuestionSkipOverridesForce(self):
        """Tests that the user is not asked for confirmation if -s is
        used and the question already exists. The entry should be
        skipped, and a new one will be read. This version checks that
        -s overrides a previous -f."""
        self.baseTestExistingQuestionSkip(argv=["-f", "-s"])

    def testExistingAnswerConfirm(self):
        """Tests that the user is asked for confirmation if the
        answer already exists, and that the entry is added if the
        user says 'y'."""
        self.run_program(stdin="foo\nun orteil\ny\nFrench (Body parts)")
        final_rows = self.get_entries()
        self.assertIn("Proceed?", self.str_stdout)
        self.assertEquals((29, "foo", "un orteil", "French (Body parts)"),
                          final_rows[-1])

    def testExistingAnswerReject(self):
        """Tests that the user is asked for confirmation if the
        category does not exist yet, and that the entry is *not* added
        if the user says anything but 'y' or 'yes'."""
        self.run_program(stdin="foo\nn\nun orteil\nFrench (Body parts)")
        final_rows = self.get_entries()
        self.assertIn("Proceed?", self.str_stdout)
        self.assertEquals(28, final_rows[-1][0])

    def testExistingAnswerForce(self):
        """Tests that the user is not asked for confirmation if -f is
        used, even if the answer already exists. The entry should be
        added as is."""
        new_row = (29, "foo", "un orteil", "French (Body parts)")
        self.run_program(argv=["-f"], stdin="\n".join(new_row[1:]))
        self.assertEquals(new_row, self.get_entries()[-1])

    def testExistingAnswerSkip(self):
        """Tests that the user is not asked for confirmation if -s is
        used and the answer already exists. The entry should be
        skipped, and a new one will be read."""
        existing_prefix = ("foo", "un orteil")
        new_row = (29, "foo", "bar", "French (Body parts)")
        self.run_program(
            argv=["-s"],
            stdin="\n".join(existing_prefix + new_row[1:]))
        self.assertEquals(new_row, self.get_entries()[-1])

    def testNewCategoryConfirm(self):
        """Tests that the user is asked for confirmation if the
        category does not exist yet, and that the entry is added if
        the user says 'y'."""
        self.run_program(stdin="a\nb\nc\ny")
        final_rows = self.get_entries()
        self.assertIn("Proceed?", self.str_stdout)
        self.assertEquals((29, "a", "b", "c"), final_rows[-1])

    def testNewCategoryReject(self):
        """Tests that the user is asked for confirmation if the
        category does not exist yet, and that the entry is *not* added
        if the user says anything but 'y' or 'yes'."""
        self.run_program(stdin="a\nb\nc\nn")
        final_rows = self.get_entries()
        self.assertIn("Proceed?", self.str_stdout)
        self.assertEquals(28, final_rows[-1][0])

    def testNewCategoryForce(self):
        """Tests that the user is not asked for confirmation if -f is
        used and the category does not exist yet. The entry should be
        added as is."""
        new_row = (29, "a", "b", "c")
        self.run_program(argv=["-f"], stdin="\n".join(new_row[1:]))
        self.assertEquals(new_row, self.get_entries()[-1])

    def testNewCategorySkip(self):
        """Tests that the user is not asked for confirmation if -s is
        used and the category does not exist yet. The entry should be
        skipped, and the next one should be read."""
        skipped_row = ("a", "b", "c")
        new_row = (29, "a", "b", "French (Body parts)")
        self.run_program(argv=["-s"],
                         stdin="\n".join(skipped_row + new_row[1:]))
        self.assertEquals(new_row, self.get_entries()[-1])

if __name__ == "__main__":
    unittest.main()
