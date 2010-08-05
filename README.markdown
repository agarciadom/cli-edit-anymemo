What is this project?
---------------------

It is a simple script for adding in bulk questions and answers to an
AnyMemo SQLite database, with checks for repeated questions and
answers and tab-completion for categories.

Entries are read from standard input. Nothing is committed to disk
until the end of the input is reached (when reading from a file) or
until the user presses Ctrl+D (when running from a console). If the
script is run from a console, Ctrl+C can be used to exit without
saving any changes.

What is its license?
--------------------

This project is under the MIT license. Hack at will... even though
there's not much to hack :-).
