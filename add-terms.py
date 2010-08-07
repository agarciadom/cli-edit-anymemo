#!/usr/bin/python3.1
"""Simple script for adding in bulk questions and answers to an
AnyMemo SQLite database, with checks for repeated questions and
answers and tab-completion for categories.

Entries are read from standard input. Nothing is committed to disk
until the end of the input is reached (when reading from a file) or
until the user presses Ctrl+D (when running from a console). If the
script is run from a console, Ctrl+C can be used to exit without
saving any changes."""

# Bulk add script for AnyMemo SQLite databases (tested with AnyMemo 5.3.2)
# Copyright (c) 2010 Antonio García-Domínguez <nyoescape@gmail.com>
# Available under the MIT license:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sqlite3
import logging
import readline

##### CONSTANTS ###############################################################

VERSION = "1.1.2"

# Default values
DEFAULT_DATABASE = "mydatabase.xml.db"

# Enum for what to do when an entry with the same question and/or
# answer exists
EXISTING_ASK, EXISTING_SKIP, EXISTING_ADD = range(3)

###############################################################################


class CategoryCompleter(object):
    """Category completer."""

    def __init__(self, db_cursor):
        db_cursor.execute('SELECT DISTINCT category FROM dict_tbl')
        self.categories = [r[0] for r in db_cursor]
        logging.debug('Categories for autocomplete: '
                      + ', '.join(self.categories))

    def complete(self, text, state):
        options = [c for c in self.categories if c.startswith(text)]
        if state < len(options):
            return options[state]
        else:
            return None

    def add_category(self, new_category):
        if new_category and new_category not in self.categories:
            self.categories.append(new_category)


def confirm(question):
    answer = input(question + " [y/n] ").strip().lower()
    if answer in ("y", "yes"):
        return True
    else:
        return False


def check_existing(msg_generator, exists, return_value, when_existing):
    if exists and when_existing != EXISTING_ADD:
        if (when_existing == EXISTING_ASK
            and confirm(msg_generator(exists, return_value))):
            return return_value
    elif return_value:
        return return_value


def ask_for_question(db_cursor, when_existing):
    question = input('Question: ').strip()
    db_cursor.execute(
        'SELECT answer FROM dict_tbl WHERE trim(question)=?',
        (question,))

    rows = db_cursor.fetchall()
    logging.debug("Answers for '{0}': {1:d}".format(question, len(rows)))
    return check_existing(
        msg_generator=lambda rows, question:
            ("Question '{question}' seems to exist already, with "
             + "answer '{answer}'. Proceed?").format(question=question,
                                                     answer=rows[0][0]),
        exists=rows,
        return_value=question,
        when_existing=when_existing)


def ask_for_answer(db_cursor, when_existing):
    answer = input('Answer: ').strip()
    db_cursor.execute(
        'SELECT question FROM dict_tbl WHERE trim(answer)=?',
        (answer,))

    rows = db_cursor.fetchall()
    logging.debug("Questions for '{0}': {1:d}".format(answer, len(rows)))
    return check_existing(
        msg_generator=lambda rows, question:
            ("Answer '{answer}' seems to exist already, with "
             + "question '{question}'. Proceed?").format(question=rows[0][0],
                                                         answer=answer),
        exists=rows,
        return_value=answer,
        when_existing=when_existing)


def ask_for_category(db_cursor, completer, when_existing, last_category):
    readline.parse_and_bind("tab: complete")
    readline.set_completer(completer.complete)
    category = input("Category{}: "
                     .format(" (default is " + last_category + ")"
                             if last_category else "")).strip()
    readline.set_completer(None)
    if not category:
        category = last_category

    db_cursor.execute(
        'SELECT count(*) FROM dict_tbl WHERE category=?',
        (category,))
    count = int(db_cursor.fetchone()[0])

    if check_existing(msg_generator=lambda pred, category:
        "Category '{}' does not seem to exist. Proceed?".format(category),
        exists=count == 0,
        return_value=category,
        when_existing=when_existing):

        completer.add_category(category)
        return category


def ask_for_entries(database_path, when_existing):
    """Asks for a series of questions/answers from the standard input,
    and adds them to the SQLite DB in the specified absolute
    path. Warns when the question or answer already exists."""
    conn = sqlite3.connect(database_path)
    db_c = conn.cursor()
    last_category = None
    cat_completer = CategoryCompleter(db_c)

    logging.info("Opened database '{}'".format(database_path))
    print("""
Press Ctrl+D at any time to exit saving changes, or Ctrl+C to exit
without saving changes. Autocomplete categories with TAB. If you want
to cancel adding some entry without exiting the program, enter an
empty question or an empty answer.
""")

    try:
        while True:
            question = ask_for_question(db_c, when_existing)
            if not question:
                logging.debug("No question: looping back to start")
                continue
            logging.debug("Got question '{}'".format(question))

            answer = ask_for_answer(db_c, when_existing)
            if not answer:
                logging.debug("No answer: looping back to start")
                continue
            logging.debug("Got answer '{}'".format(answer))

            category = ask_for_category(db_c, cat_completer,
                                        when_existing, last_category)
            if not category:
                logging.debug("No category: looping back to start")
                continue
            else:
                last_category = category
                logging.debug("Got category '{}'".format(category))

            db_c.execute(
                'INSERT INTO dict_tbl (question, answer, category) '
                + 'VALUES (?, ?, ?)',
                (question, answer, category))
            db_c.execute(
                'INSERT INTO learn_tbl (date_learn, interval, grade, easiness,'
                + 'acq_reps, ret_reps, lapses, acq_reps_since_lapse, '
                + 'ret_reps_since_lapse) VALUES '
                + '(?,?,?,?,?,?,?,?,?)',
                ('2010-01-01', 0, 0, 2.5, 0, 0, 0, 0, 0))

            logging.info("New entry: '{}' -> '{}' (category '{}')"
                         .format(question, answer, category))
    except EOFError:
        logging.info("Saving changes...")
        conn.commit()
    except KeyboardInterrupt:
        logging.info("Exiting without saving changes...")
    finally:
        logging.info("Exiting...")
        conn.close()

if __name__ == "__main__":
    from optparse import OptionParser
    import sys
    from os.path import realpath

    parser = OptionParser(description=__doc__, version=VERSION)
    parser.add_option(
        "--database", "-d", dest="database",
        default=DEFAULT_DATABASE, type=str,
        help="Set the SQLite DB file to be modified ({} by default)"
             .format(DEFAULT_DATABASE))
    parser.add_option(
        "--force", "-f", dest="when_existing",
        action="store_const", const=EXISTING_ADD, default=EXISTING_ASK,
        help="Add new entries without confirmation even if the questions "
             + "and/or answers exist, or the category does not exist yet "
             + "(overrides a previous -s)")
    parser.add_option(
        "--skip-existing", "-s", dest="when_existing",
        action="store_const", const=EXISTING_SKIP, default=EXISTING_ASK,
        help="Skip entries without confirmation if the questions "
             + "and/or answers exist, or the category does not exist yet "
             + "(overrides a previous -f)")
    parser.add_option(
        "--verbose", "-v", dest="verbose",
        action="store_true", default=False,
        help="Print debugging information")

    opts, args = parser.parse_args()
    if args:
        parser.print_help()
        sys.exit(1)
    if opts.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    ask_for_entries(database_path=realpath(opts.database),
                    when_existing=opts.when_existing)
