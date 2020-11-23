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

BracesAroundCodeBlocks
######################


This rule rewrites code blocks following if/else, for, while and do/while statements,
ensuring that they are surrounded by braces.

For example:

::

    if (check1())
       func1();
    else if (check2())
        if (check3())
            func2();

Becomes:

::

    if (check1())
    {
       func1();
    }
    else if (check2())
    {
        if (check3())
        {
            func2();
        }
    }

    


PrototypeFunctionDeclarations
#############################


This rule rewrites function declarations and implementations with no function
parameters, to ensure 'void' is used in place of function parameters.

For example:

::

    void function();

    void function()
    {
        return;
    }

Becomes:

::

    void function(void);

    void function(void)
    {
        return;
    }

    


OneDeclarationPerLine
#####################


This rule rewrites lines that declare & initialize multiple values in a single
statement, to separate each declaration + initialization on its own line and
statement.

For example:

::

   static const int a = 2, *b = NULL, **c = NULL;

Becomes:

::

    static const int a = 2;
    static const int *b = NULL;
    static const int **c = NULL;

    


InitializeCanonicals
####################


This rule rewrites declarations of canonical data types that have no initial
value, and adds a sane initial value.

For example:

::

    volatile float x, *X;
    static const bool y;
    short *z;

Becomes:

::

    volatile float x = 0.0f, *X = NULL;
    static const bool y = false;
    short *z = NULL;

    


TerminateElseIfWithElse
#######################


Rewrites else-if chains to ensure they are terminated with an 'else' clause.

For example:

::

    if (check1())
    {
        func1();
    }
    else if (check2())
    {
        func2();
    }

Becomes:

::

    if (check1())
    {
        func1();
    }
    else if (check2())
    {
        func2();
    }
    else
    {
        ;
    }

    


ExplicitUnusedFunctionParams
############################


This rule rewrites function implementations to explicitly mark unused function
parameters with "void".

For example:

::

    int func(int a, int b)
    {
        return b + 2;
    }

Becomes:

::

    int func(int a, int b)
    {
        (void) a;

        return b + 2;
    }
    


