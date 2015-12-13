"""
Check code quality using pep8, pylint, and diff_quality.
"""
import os
import re

from paver.easy import sh, BuildFailure


# class EnvClass(object):
#     ROOT_DIR = None
#     REPORT_DIR = None
#     METRICS_DIR = None


# Env = EnvClass()
# Env.ROOT_DIR = path(__file__).abspath().parent.parent
# Env.REPORT_DIR = Env.ROOT_DIR / path(__file__).abspath().parent / 'reports'
# Env.METRICS_DIR = Env.ROOT_DIR / path(__file__).abspath().parent / 'metrics'


def top_python_dirs(dirname):
    """
    Find the directories to start from in order to find all the Python files in `dirname`.
    """
    top_dirs = []

    dir_init = os.path.join(dirname, "__init__.py")
    if os.path.exists(dir_init):
        top_dirs.append(dirname)

    for directory in ['djangoapps', 'lib']:
        subdir = os.path.join(dirname, directory)
        subdir_init = os.path.join(subdir, "__init__.py")
        if os.path.exists(subdir) and not os.path.exists(subdir_init):
            dirs = os.listdir(subdir)
            top_dirs.extend(d for d in dirs if os.path.isdir(os.path.join(subdir, d)))

    return top_dirs


def _count_pylint_violations(report_file):
    """
    Parses a pylint report line-by-line and determines the number of violations reported
    """
    num_violations_report = 0
    # An example string:
    # common/lib/xmodule/xmodule/tests/test_conditional.py:21: [C0111(missing-docstring), DummySystem] Missing docstring
    # More examples can be found in the unit tests for this method
    pylint_pattern = re.compile(r".(\d+):\ \[(\D\d+.+\]).")

    for line in open(report_file):
        violation_list_for_line = pylint_pattern.split(line)
        # If the string is parsed into four parts, then we've found a violation. Example of split parts:
        # test file, line number, violation name, violation details
        if len(violation_list_for_line) == 4:
            num_violations_report += 1
    return num_violations_report


def _get_pep8_violations(report_path):
    """
    Runs pep8. Returns a tuple of (number_of_violations, violations_string)
    where violations_string is a string of all pep8 violations found, separated
    by new lines.
    """
    report_dir = (report_path / 'pep8')
    report_dir.rmtree(ignore_errors=True)
    report_dir.makedirs_p()

    # Make sure the metrics subdirectory exists
    # Env.METRICS_DIR.makedirs_p()

    sh(
        'pep8 ' + report_dir + ' --max-line-length=120 --exclude="*migrations*,dev/*"  | tee {report_dir}/pep8.report -a '.format(
            report_dir=report_dir))

    count, violations_list = _pep8_violations(
        "{report_dir}/pep8.report".format(report_dir=report_dir)
    )

    return (count, violations_list)


def _pep8_violations(report_file):
    """
    Returns a tuple of (num_violations, violations_list) for all
    pep8 violations in the given report_file.
    """
    with open(report_file) as f:
        violations_list = f.readlines()
    num_lines = len(violations_list)
    return num_lines, violations_list


def _write_metric(metric, filename):
    """
    Write a given metric to a given file
    Used for things like reports/metrics/jshint, which will simply tell you the number of
    jshint violations found
    """
    with open(filename, "w") as metric_file:
        metric_file.write(str(metric))


def _prepare_report_dir(dir_name):
    """
    Sets a given directory to a created, but empty state
    """
    dir_name.rmtree_p()
    dir_name.mkdir_p()


def _get_last_report_line(filename):
    """
    Returns the last line of a given file. Used for getting output from quality output files.
    """
    file_not_found_message = "The following log file could not be found: {file}".format(file=filename)
    if os.path.isfile(filename):
        with open(filename, 'r') as report_file:
            lines = report_file.readlines()
            return lines[len(lines) - 1]
    else:
        # Raise a build error if the file is not found
        raise BuildFailure(file_not_found_message)


def _get_count_from_last_line(filename, file_type):
    """
    This will return the number in the last line of a file.
    It is returning only the value (as a floating number).
    """
    last_line = _get_last_report_line(filename)
    if file_type is "python_complexity":
        # Example of the last line of a complexity report: "Average complexity: A (1.93953443446)"
        regex = r'\d+.\d+'
    else:
        # Example of the last line of a jshint report (for example): "3482 errors"
        regex = r'^\d+'

    try:
        return float(re.search(regex, last_line).group(0))
    # An AttributeError will occur if the regex finds no matches.
    # A ValueError will occur if the returned regex cannot be cast as a float.
    except (AttributeError, ValueError):
        return None


def run_quality(output_path, options):
    """
    output_path: expects the output path of the the type Path.py
    """
    dquality_dir = (output_path / "diff_quality").makedirs_p()

    # Save the pass variable. It will be set to false later if failures are detected.
    diff_quality_percentage_pass = True

    def _pep8_output(count, violations_list, is_html=False):
        """
        Given a count & list of pep8 violations, pretty-print the pep8 output.
        If `is_html`, will print out with HTML markup.
        """
        if is_html:
            lines = ['<body>\n']
            sep = '-------------<br/>\n'
            title = "<h1>Quality Report: pep8</h1>\n"
            violations_bullets = ''.join(
                ['<li>{violation}</li><br/>\n'.format(violation=violation) for violation in violations_list]
            )
            violations_str = '<ul>\n{bullets}</ul>\n'.format(bullets=violations_bullets)
            violations_count_str = "<b>Violations</b>: {count}<br/>\n"
            fail_line = "<b>FAILURE</b>: pep8 count should be 0<br/>\n"
        else:
            lines = []
            sep = '-------------\n'
            title = "Quality Report: pep8\n"
            violations_str = ''.join(violations_list)
            violations_count_str = "Violations: {count}\n"
            fail_line = "FAILURE: pep8 count should be 0\n"

        violations_count_str = violations_count_str.format(count=count)

        lines.extend([sep, title, sep, violations_str, sep, violations_count_str])

        if count > 0:
            lines.append(fail_line)
        lines.append(sep + '\n')
        if is_html:
            lines.append('</body>')

        return ''.join(lines)

    # Run pep8 directly since we have 0 violations on master
    (count, violations_list) = _get_pep8_violations(output_path)

    # Print number of violations to log
    print _pep8_output(count, violations_list)

    # Also write the number of violations to a file
    with open(dquality_dir / "diff_quality_pep8.html", "w") as f:
        f.write(_pep8_output(count, violations_list, is_html=True))

    if count > 0:
        diff_quality_percentage_pass = False

    # ----- Set up for diff-quality pylint call -----
    # Set the string, if needed, to be used for the diff-quality --compare-branch switch.
    compare_branch = getattr(options, 'compare_branch', None)
    compare_branch_string = u''
    if compare_branch:
        compare_branch_string = u'--compare-branch={0}'.format(compare_branch)

    # Set the string, if needed, to be used for the diff-quality --fail-under switch.
    diff_threshold = int(getattr(options, 'percentage', -1))
    percentage_string = u''
    if diff_threshold > -1:
        percentage_string = u'--fail-under={0}'.format(diff_threshold)

    # Generate diff-quality html report for pylint, and print to console
    # If pylint reports exist, use those
    # Otherwise, `diff-quality` will call pylint itself

    pylint_files = get_violations_reports(output_path, "pylint")
    pylint_reports = u' '.join(pylint_files)
    jshint_files = get_violations_reports(output_path, "jshint")
    jshint_reports = u' '.join(jshint_files)

    # run diff-quality for pylint.

    # If one of the quality runs fails, then paver exits with an error when it is finished


def run_diff_quality(violations_type=None, prefix=None, reports=None, percentage_string=None, branch_string=None,
                     dquality_dir=None):
    """
    This executes the diff-quality commandline tool for the given violation type (e.g., pylint, jshint).
    If diff-quality fails due to quality issues, this method returns False.

    """
    try:
        sh(
            "{pythonpath_prefix} diff-quality --violations={type} "
            "{reports} {percentage_string} {compare_branch_string} "
            "--html-report {dquality_dir}/diff_quality_{type}.html ".format(
                type=violations_type,
                pythonpath_prefix=prefix,
                reports=reports,
                percentage_string=percentage_string,
                compare_branch_string=branch_string,
                dquality_dir=dquality_dir,
            )
        )
        return True
    except BuildFailure, error_message:
        if is_percentage_failure(error_message):
            return False
        else:
            raise BuildFailure(error_message)


def is_percentage_failure(error_message):
    """
    When diff-quality is run with a threshold percentage, it ends with an exit code of 1. This bubbles up to
    paver with a subprocess return code error. If the subprocess exits with anything other than 1, raise
    a paver exception.
    """
    if "Subprocess return code: 1" not in error_message:
        return False
    else:
        return True


def get_violations_reports(report_path, violations_type):
    """
    Finds violations reports files by naming convention (e.g., all "pep8.report" files)
    """
    violations_files = []
    for subdir, _dirs, files in os.walk(os.path.join(report_path)):
        for f in files:
            if f == "{violations_type}.report".format(violations_type=violations_type):
                violations_files.append(os.path.join(subdir, f))
    return violations_files
