#!/usr/bin/python3.1
"""Adds a set of questions and answers to an AnyMemo SQLite
database. Entries are read from standard input."""

VERSION = "1.1"

# Default values
DEFAULT_DATABASE = "germanpod.xml.db"

import sqlite3
import logging
import readline

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


def confirm(question):
    answer = input(question + " [y/n] ").strip().lower()
    if answer in ("y", "yes"):
        return True
    else:
        return False

def ask_for_question(db_cursor, force):
    question = input('Question: ').strip()
    db_cursor.execute(
        'SELECT answer FROM dict_tbl WHERE trim(question)=?',
        (question,))

    rows = db_cursor.fetchall()
    logging.debug("Answers for '{0}': {1:d}".format(question, len(rows)))
    if rows and not force:
        ex_answer = rows[0][0]
        if confirm(
            ("Question '{question}' seems to exist already, with "
             + "answer '{answer}'. Proceed?").format(question=question,
                                                     answer=ex_answer)):
            return question
    elif question:
        return question


def ask_for_answer(db_cursor, force):
    answer = input('Answer: ').strip()
    db_cursor.execute(
        'SELECT question FROM dict_tbl WHERE trim(answer)=?',
        (answer,))

    rows = db_cursor.fetchall()
    logging.debug("Questions for '{0}': {1:d}".format(answer, len(rows)))
    if rows and not force:
        ex_question = rows[0][0]
        if confirm(
            ("Answer '{answer}' seems to exist already, with "
             + "question '{question}'. Proceed?").format(question=ex_question,
                                                         answer=answer)):
            return answer
    elif answer:
        return answer


def ask_for_category(db_cursor, completer, force, last_category):
    readline.parse_and_bind("tab: complete")
    readline.set_completer(completer)
    category = input("Category{}: "
                     .format(" (default is )" + last_category
                             if last_category else "")).strip()
    readline.set_completer(None)
    if not category:
        category = last_category

    db_cursor.execute(
        'SELECT count(*) FROM dict_tbl WHERE category=?',
        (category,))
    count = int(db_cursor.fetchone()[0])

    if count == 0 and not force:
        if confirm("Category '{}' does not seem to exist. Proceed?"
                   .format(category)):
            return category
    elif category:
        return category


def ask_for_entries(database_path, force):
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
without saving changes. Autocomplete categories with TAB.
""")

    try:
        while True:
            question = ask_for_question(db_c, force)
            if not question:
                logging.debug("No question: looping back to start")
                continue
            logging.debug("Got question '{}'".format(question))

            answer = ask_for_answer(db_c, force)
            if not answer:
                logging.debug("No answer: looping back to start")
                continue
            logging.debug("Got answer '{}'".format(answer))

            category = ask_for_category(db_c, cat_completer.complete, force, last_category)
            if not category:
                logging.debug("No category: looping back to start")
                continue
            else:
                last_category = category
                logging.debug("Got category '{}'".format(category))

            db_c.execute(
                'INSERT INTO dict_tbl (question, answer, category) VALUES (?,?,?)',
                (question, answer, category))
            db_c.execute(
                'INSERT INTO learn_tbl (date_learn, interval, grade, easiness, '
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
        "--force", "-f", dest="force",
        action="store_true", default=False,
        help="Add new entries without confirmation even if the questions "
             + "and/or answers exist")
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

    ask_for_entries(database_path=realpath(opts.database), force=opts.force)
