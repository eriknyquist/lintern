from lintern.rewriter import rewrite_rules

ULINE_CHAR = '#'

for r in rewrite_rules:
    name = r.__class__.__name__
    underline = ULINE_CHAR * len(name)
    text = r.__doc__

    print(name + '\n' + underline + "\n\n" + text + "\n\n")
