# Copyright 2013 Rackspace
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import ConfigParser
import contextlib
import datetime
import os
import subprocess
import sys

import git
import cli_tools


@contextlib.contextmanager
def with_branch(output, repo, branch):
    """
    A contextmanager function which ensures that operations on a given
    repository are done with a specific branch checked out.

    :param output: An Output object to which the command outputs will
                   be sent.
    :param repo: The repository being acted upon.
    :param branch: The desired branch.
    """

    save_branch = repo.get_current_branch()
    if save_branch != branch:
        output.send("Current branch %s; switching to %s" %
                    (save_branch, branch))
        repo.git_checkout(output, branch)

    try:
        yield
    finally:
        if save_branch != branch:
            output.send("Returning to original branch %s" % save_branch)
            repo.git_checkout(output, save_branch)


class Repo(object):
    """
    Describe a repository to be freshened.
    """

    def __init__(self, name, basedir='~/devel/src',
                 pull='origin', push=None,
                 branch='master', install_mode=None):
        """
        Initialize a Repo object.

        :param name: The name of the repository.
        :param basedir: The base directory the repository can be found
                        in.  It is expected that the repository will
                        be stored under "basedir/name".  This
                        parameter will be tilde-expanded.
        :param pull: The remote to pull changes from during a freshen.
        :param push: The remote to push changes to during a freshen.
                     The push will be done with the "--force" option
                     to "git push".  If None, no push will be done.
        :param branch: The branch to be concerned with.
        :param install_mode: If specified, the contents of the
                             repository will be installed with the
                             specified command passed to the setup.py.
                             Suggested values are "develop" and
                             "install".
        """

        self.name = name
        self.basedir = os.path.expanduser(basedir)
        self.pull = pull
        self.push = push
        self.branch = branch
        self.install_mode = install_mode

        self.directory = os.path.join(self.basedir, name)

        self._handle = None

    def freshen(self, output):
        """
        Freshens a repository; that is, the desired branch will be
        fetched from the configured remote and the repository
        installed according to the setting of "install_mode".

        :param output: An Output object to which the command outputs
                       will be sent.
        """

        with with_branch(output, self, self.branch):
            self.git_fetch(output)
            self.git_pull(output)
            self.git_push(output)
            self.install(output)

    def get_current_branch(self):
        """
        Returns the current branch for this repository.

        :returns: The name of the current branch.
        """

        for branch in self.handle.branch().split('\n'):
            if branch.startswith('*'):
                return branch[2:]

    def git_checkout(self, output, branch):
        """
        Checks out the desired branch.

        :param output: An Output object to which the command outputs
                       will be sent.
        :param branch: The branch to check out.
        """

        output.send(self.handle.checkout(branch))

    def git_fetch(self, output):
        """
        Perform a "git fetch" operation from the default remote.

        :param output: An Output object to which the command outputs
                       will be sent.
        """

        output.send("Fetching changes from origin")
        output.send(self.handle.fetch())

    def git_pull(self, output):
        """
        Perform a "git pull" operation from the configured remote.

        :param output: An Output object to which the command outputs
                       will be sent.
        """

        if not self.pull:
            return

        output.send("Pulling in changes from %s" % self.pull)
        output.send(self.handle.pull(self.pull, self.branch))

    def git_push(self, output):
        """
        Perform a "git push" operation to the configured remote.  The
        push will be done with the "--force" flag.

        :param output: An Output object to which the command outputs
                       will be sent.
        """

        if not self.push:
            return

        output.send("Pushing out changes to %s" % self.push)
        output.send(self.handle.push('--force', self.push, self.branch))

    def install(self, output):
        """
        Install the repository according to the configured install
        mode.

        :param output: An Output object to which the command outputs
                       will be sent.
        """

        if not self.install_mode:
            return

        cmd = ['sudo', 'python', 'setup.py', self.install_mode]
        output.send("Installing repository %s with command %r" %
                    (self.name, ' '.join(cmd)))

        install = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, cwd=self.directory)
        out, err = install.communicate()

        if out:
            output.send("Stdout:", out)
        if err:
            output.send("Stderr:", err)

    def git_gc(self, output):
        """
        Perform a "git gc" operation.

        :param output: An Output object to which the command outputs
                       will be sent.
        """

        output.send(self.handle.gc())

    @property
    def handle(self):
        """
        Retrieve a GitPython handle for the repository.
        """

        if self._handle is None:
            self._handle = git.Git(self.directory)
        return self._handle


class Output(object):
    """
    A class to generate output to both a log file and to standard
    output.
    """

    def __init__(self, logfile):
        """
        Initialize an Output object.

        :param logfile: The log file name.
        """

        self.logfile = logfile
        self.log = None

    def __enter__(self):
        """
        Opens the log file upon entry to a "with" statement.

        :returns: The Output object.
        """

        self.log = open(self.logfile, 'a', 0)
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        """
        Closes the log file upon exit from a "with" statement.

        :param exc_type: The type of the exception that occurred, or
                         None.
        :param exc_value: The actual exception that occurred, or None.
        :param exc_tb: The traceback for the exception, or None.
        """

        self.log.close()
        self.log = None

    def send(self, *msgs):
        """
        Send one or more messages to the log file and to standard
        output.  Each positional argument is rendered independently,
        and forced to be output with a trailing "\n".
        """

        for msg in msgs:
            if not msg:
                continue
            elif not msg.endswith('\n'):
                msg += '\n'

            if self.log:
                self.log.write(msg)
            sys.stdout.write(msg)


def get_repos(cfg, repo_list=None):
    """
    Load a list of repositories from a repository configuration file.

    :param cfg: A ConfigParser.ConfigParser instance containing the
                configuration.
    :param repo_list: If provided, a list of repositories to be
                      operated on.  Overrides any configuration in the
                      configuration file.

    :returns: A list of Repo objects containing the repositories to
              act upon.
    """

    if not repo_list:
        try:
            repo_list = [r.strip() for r in
                         cfg.get('repos', 'list').split(',') if r]
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            repo_list = []
            for sect in cfg.sections():
                if sect.startswith('repo:'):
                    repo_list.append(sect[5:])

    repos = []
    for repo in repo_list:
        sect = 'repo:%s' % repo

        # Ensure there's a section for the repository, so we get
        # anything configured in [DEFAULT]...
        try:
            cfg.add_section(sect)
        except ConfigParser.DuplicateSectionError:
            pass

        kwargs = dict(name=repo)
        kwargs.update(dict(cfg.items('repo:%s' % repo)))

        repos.append(Repo(**kwargs))

    return repos


def prepare(repo_conf, logfile, restrict):
    """
    Prepare for either a "freshen" or "compact".  Loads the repository
    configuration and generates an Output object, which will be
    returned as a tuple.

    :param repo_conf: The repository configuration file.  Will be
                      tilde-expanded.
    :param logfile: The output log file.  Will be tilde-expanded.
    ;param restrict: A possibly empty list of repositories that the
                     operation should be restricted to.  If None or
                     empty, all configured repositories will be
                     operated on.

    :returns: A tuple of the list of Repo objects and the Output
              object.
    """

    cfg = ConfigParser.SafeConfigParser()
    cfg.read(os.path.expanduser(repo_conf))

    if logfile is None:
        try:
            logfile = cfg.get('repos', 'logfile')
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            logfile = '~/freshen.log'

    repos = get_repos(cfg, restrict)
    output = Output(os.path.expanduser(logfile))

    return repos, output


@cli_tools.argument('restrict',
                    metavar='repo',
                    nargs='*',
                    help="Restrict freshening to a set of repositories.")
@cli_tools.argument('--repo-conf', '-c',
                    default='~/.repos.ini',
                    help="Location of the repositories configuration file.")
@cli_tools.argument('--logfile', '-l',
                    default=None,
                    help="Location of the log file, for output.")
def freshen(repo_conf, logfile=None, restrict=None):
    """
    Refresh a configured branch of a list of repositories to track
    their upstream.

    :param repo_conf: The repository configuration file.  Will be
                      tilde-expanded.
    :param logfile: The name of a log file.  If not provided, the file
                    will be derived from the configuration.  If not
                    configured, a default will be used.
    :param restrict: Optional; a list of repositories that the freshen
                     operation should be restricted to.
    """

    repos, output = prepare(repo_conf, logfile, restrict)

    with output:
        output.send("Freshening repositories at %s" %
                    datetime.datetime.now())
        for repo in repos:
            output.send("Freshening repository %s..." % repo.name)
            repo.freshen(output)


@cli_tools.argument('restrict',
                    metavar='repo',
                    nargs='*',
                    help="Restrict freshening to a set of repositories.")
@cli_tools.argument('--repo-conf', '-c',
                    default='~/.repos.ini',
                    help="Location of the repositories configuration file.")
@cli_tools.argument('--logfile', '-l',
                    default=None,
                    help="Location of the log file, for output.")
def compact(repo_conf, logfile=None, restrict=None):
    """
    Compact a list of repositories--that is, call "git gc" on the
    repositories.

    :param repo_conf: The repository configuration file.  Will be
                      tilde-expanded.
    :param logfile: The name of a log file.  If not provided, the file
                    will be derived from the configuration.  If not
                    configured, a default will be used.
    :param restrict: Optional; a list of repositories that the compact
                     operation should be restricted to.
    """

    repos, output = prepare(repo_conf, logfile, restrict)

    with output:
        output.send("Compacting repositories at %s" %
                    datetime.datetime.now())
        for repo in repos:
            output.send("Compacting repository %s..." % repo.name)
            repo.git_gc(output)
