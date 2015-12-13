A simple pep8 quality test
==========================

Do you think your code is clean??!!

run quality_test on your home directory and find out how many violations your code have.

Simple installation using pip:

"pip install pep-quality"

use the following to test your code:

"
from path import Path as path
from pep_quality.quality import run_quality

...
...
...

run_quality(path(__file__).abspath(), None)
"
