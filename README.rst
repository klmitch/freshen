================================
Tool for Refreshing Repositories
================================

This is a tool for refreshing a set of git repositories.  That is, for
each configured repository, a ``git pull`` followed by an optional
``git push`` will be performed, to cause the ``master`` branch to
track an upstream project.  The repository may also be installed on
the system; this will be done by calling ``sudo python setup.py
install`` or ``sudo python setup.py develop``, so ``sudo`` access will
be required to use this feature.

``freshen`` Tool Usage
======================

The ``freshen`` tool performs the freshening operation described
above.  A usage summary follows::

    usage: [-h] [--repo-conf REPO_CONF] [--logfile LOGFILE] [repo [repo ...]]

    Refresh a configured branch of a list of repositories to track their upstream.

    positional arguments:
      repo                  Restrict freshening to a set of repositories.

    optional arguments:
      -h, --help            show this help message and exit
      --repo-conf REPO_CONF, -c REPO_CONF
                            Location of the repositories configuration file.
      --logfile LOGFILE, -l LOGFILE
                            Location of the log file, for output.

``compact`` Tool Usage
======================

The ``compact`` tool performs a ``git gc`` on the configured
repositories.  A usage summary follows::

    usage: [-h] [--repo-conf REPO_CONF] [--logfile LOGFILE] [repo [repo ...]]

    Compact a list of repositories--that is, call "git gc" on the repositories.

    positional arguments:
      repo                  Restrict freshening to a set of repositories.

    optional arguments:
      -h, --help            show this help message and exit
      --repo-conf REPO_CONF, -c REPO_CONF
                            Location of the repositories configuration file.
      --logfile LOGFILE, -l LOGFILE
                            Location of the log file, for output.

Repositories Configuration File
===============================

The repositories configuration file used by ``freshen`` and
``compact`` is an INI-style configuration file.  Each repository is
described using a "[repo:<name>]" section, where "<name>" is the name
of the repository as it will appear in a list of repositories.  Valid
configuration options for each repository can include:

name
    This allows the name of the repository to be overridden.

basedir
    The base directory in which the repository may be located.  Will
    be tilde-expanded.  Defaults to "~/devel/src".

pull
    The name of the configured remote from which to pull.  Defaults to
    "origin".

push
    The name of the configured remote to which to push.  If not
    specified, no push will be performed.

branch
    The branch to pull.  Defaults to "master".

install_mode
    If the repository should be installed after refreshing, set this
    option to one of "install" or "develop".  This will be the command
    given to the repository's ``setup.py``.

Any of these options may also be set in the "[DEFAULT]" section.  In
addition, the list of repositories may be specified explicitly, as a
comma-separated list in the "[repos]" section; the option is "list".
Repositories listed in this option do not need explicit sections,
except to override or add additional configuration over that specified
in "[DEFAULT]".

In addition, the default log file can also be set in the "[repos]"
section, using the "logfile" option.  Of course, the logfile specified
on the command line will be used in preference, but if it is not
specified, it will default to "~/freshen.log"; again, this option will
be tilde-expanded.
