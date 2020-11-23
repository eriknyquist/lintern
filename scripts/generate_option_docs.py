import shutil
from lintern.rewriter import rewrite_rules

README = 'README.rst'
README_TEMPLATE = 'README_template.rst'
ULINE_CHAR = '#'

shutil.copyfile(README_TEMPLATE, README)

doctext = ""
for r in rewrite_rules:
    name = r.__class__.__name__
    underline = ULINE_CHAR * len(name)
    text = r.__doc__

    doctext += (name + '\n' + underline + "\n\n" + text + "\n\n\n")

with open(README, 'a+') as wfh:
    wfh.write(doctext)
