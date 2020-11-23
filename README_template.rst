lintern
-------

Python-based tool which uses ``libclang`` to rewrite C code to fix certain things
that static analysis checkers often complain about. Not particularly fancy, just
takes care of some of the more mindless things that are annoying for humans to
waste their time on, that's all.

You should probably use ``clang-tidy`` instead.

Source code formatting / whitespace
===================================

Lintern makes a reasonable effort to indent new lines in a way consistent with
surrounding lines, however there are not really any features for controlling
whitespace. Lintern is all about modifying the stream of tokens, and doesn't really
care much about whitespace.

If you need to enforce a certain coding/whitespace style, it is recommended to run
lintern first, and then run a tool focused on whitespace (such as ``clang-format``)
as a final step.


Configuration file
------------------

By default, all rewrite rules are enabled. If you want more control over which
rules are enabled, you can write a configuration file. A good starting point is to
run ``python -m lintern -g``, which will print configuration file data with all
available options enabled. You can save this output to a text file, and use it
as your configuration file once you have changed your desired options.

Lintern will look for a configuration file called `.lintern`. Alternatively,
you can pass a different config file using the ``-f`` option, e.g.
``python -m lintern -f other_config_file.txt``.


Configuration file options
==========================

