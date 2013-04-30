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
import subprocess
import sys

import mock
import unittest2

import freshen


class TestWithBranch(unittest2.TestCase):
    def test_same_branch(self):
        repo = mock.Mock(**{
            'get_current_branch.return_value': 'master',
        })
        output = mock.Mock()

        with freshen.with_branch(output, repo, 'master'):
            repo.get_current_branch.assert_called_once_with()
            self.assertFalse(output.send.called)
            self.assertFalse(repo.git_checkout.called)

            output.reset_mock()
            repo.reset_mock()

        self.assertFalse(output.send.called)
        self.assertFalse(repo.git_checkout.called)

    def test_other_branch(self):
        repo = mock.Mock(**{
            'get_current_branch.return_value': 'other',
        })
        output = mock.Mock()

        with freshen.with_branch(output, repo, 'master'):
            repo.get_current_branch.assert_called_once_with()
            output.send.assert_called_once_with(mock.ANY)
            repo.git_checkout.assert_called_once_with(output, 'master')

            output.reset_mock()
            repo.reset_mock()

        output.send.assert_called_once_with(mock.ANY)
        repo.git_checkout.assert_called_once_with(output, 'other')


class TestRepo(unittest2.TestCase):
    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    def test_init_defaults(self, mock_expanduser):
        repo = freshen.Repo('repo')

        self.assertEqual(repo.name, 'repo')
        self.assertEqual(repo.basedir, '/home/test/devel/src')
        self.assertEqual(repo.pull, 'origin')
        self.assertEqual(repo.push, None)
        self.assertEqual(repo.branch, 'master')
        self.assertEqual(repo.install_mode, None)
        self.assertEqual(repo.directory, '/home/test/devel/src/repo')
        self.assertEqual(repo._handle, None)

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    def test_init(self, mock_expanduser):
        repo = freshen.Repo('repo', basedir='~/src', pull='remote',
                            push='origin', branch='development',
                            install_mode='develop')

        self.assertEqual(repo.name, 'repo')
        self.assertEqual(repo.basedir, '/home/test/src')
        self.assertEqual(repo.pull, 'remote')
        self.assertEqual(repo.push, 'origin')
        self.assertEqual(repo.branch, 'development')
        self.assertEqual(repo.install_mode, 'develop')
        self.assertEqual(repo.directory, '/home/test/src/repo')
        self.assertEqual(repo._handle, None)

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch.object(freshen, 'with_branch', return_value=mock.MagicMock())
    @mock.patch.object(freshen.Repo, 'git_fetch')
    @mock.patch.object(freshen.Repo, 'git_pull')
    @mock.patch.object(freshen.Repo, 'git_push')
    @mock.patch.object(freshen.Repo, 'install')
    def test_freshen(self, mock_install, mock_git_push, mock_git_pull,
                     mock_git_fetch, mock_with_branch, mock_expanduser):
        repo = freshen.Repo('repo')

        repo.freshen('output')

        mock_with_branch.assert_called_once_with('output', repo, 'master')
        mock_with_branch.return_value.__enter__.assert_called_once_with()
        mock_with_branch.return_value.__exit__.assert_called_once_with(
            None, None, None)
        mock_git_fetch.assert_called_once_with('output')
        mock_git_pull.assert_called_once_with('output')
        mock_git_push.assert_called_once_with('output')
        mock_install.assert_called_once_with('output')

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch.object(freshen.Repo, 'handle', mock.Mock(**{
        'branch.return_value': '  other\n  something\n* master\n  new',
    }))
    def test_get_current_branch(self, mock_expanduser):
        repo = freshen.Repo('repo')

        result = repo.get_current_branch()

        repo.handle.branch.assert_called_once_with()
        self.assertEqual(result, 'master')

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch.object(freshen.Repo, 'handle', mock.Mock(**{
        'checkout.return_value': 'checkout return value',
    }))
    def test_git_checkout(self, mock_expanduser):
        output = mock.Mock()
        repo = freshen.Repo('repo')

        repo.git_checkout(output, 'branch')

        output.send.assert_called_once_with('checkout return value')
        repo.handle.checkout.assert_called_once_with('branch')

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch.object(freshen.Repo, 'handle', mock.Mock(**{
        'fetch.return_value': 'fetch return value',
    }))
    def test_git_fetch(self, mock_expanduser):
        output = mock.Mock()
        repo = freshen.Repo('repo')

        repo.git_fetch(output)

        output.send.assert_has_calls([
            mock.call("Fetching changes from origin"),
            mock.call("fetch return value"),
        ])
        repo.handle.fetch.assert_called_once_with()

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch.object(freshen.Repo, 'handle', mock.Mock(**{
        'pull.return_value': 'pull return value',
    }))
    def test_git_pull_none(self, mock_expanduser):
        output = mock.Mock()
        repo = freshen.Repo('repo', pull=None)

        repo.git_pull(output)

        self.assertFalse(output.send.called)
        self.assertFalse(repo.handle.pull.called)

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch.object(freshen.Repo, 'handle', mock.Mock(**{
        'pull.return_value': 'pull return value',
    }))
    def test_git_pull(self, mock_expanduser):
        output = mock.Mock()
        repo = freshen.Repo('repo')

        repo.git_pull(output)

        output.send.assert_has_calls([
            mock.call("Pulling in changes from origin"),
            mock.call("pull return value"),
        ])
        repo.handle.pull.assert_called_once_with('origin', 'master')

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch.object(freshen.Repo, 'handle', mock.Mock(**{
        'push.return_value': 'push return value',
    }))
    def test_git_push_none(self, mock_expanduser):
        output = mock.Mock()
        repo = freshen.Repo('repo')

        repo.git_push(output)

        self.assertFalse(output.send.called)
        self.assertFalse(repo.handle.push.called)

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch.object(freshen.Repo, 'handle', mock.Mock(**{
        'push.return_value': 'push return value',
    }))
    def test_git_push(self, mock_expanduser):
        output = mock.Mock()
        repo = freshen.Repo('repo', push='origin')

        repo.git_push(output)

        output.send.assert_has_calls([
            mock.call("Pushing out changes to origin"),
            mock.call("push return value"),
        ])
        repo.handle.push.assert_called_once_with('--force', 'origin', 'master')

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch.object(subprocess, 'Popen', return_value=mock.Mock(**{
        'communicate.return_value': ('', ''),
    }))
    def test_install_none(self, mock_Popen, mock_expanduser):
        output = mock.Mock()
        repo = freshen.Repo('repo')

        repo.install(output)

        self.assertFalse(output.send.called)
        self.assertFalse(mock_Popen.called)

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch.object(subprocess, 'Popen', return_value=mock.Mock(**{
        'communicate.return_value': ('', ''),
    }))
    def test_install_no_output(self, mock_Popen, mock_expanduser):
        output = mock.Mock()
        repo = freshen.Repo('repo', install_mode='install')

        repo.install(output)

        output.send.assert_has_calls([
            mock.call('Installing repository repo with command '
                      "'sudo python setup.py install'"),
        ])
        self.assertEqual(output.send.call_count, 1)
        mock_Popen.assert_called_once_with(
            ['sudo', 'python', 'setup.py', 'install'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd='/home/test/devel/src/repo')
        mock_Popen.return_value.communicate.assert_called_once_with()

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch.object(subprocess, 'Popen', return_value=mock.Mock(**{
        'communicate.return_value': ('standard output', 'standard error'),
    }))
    def test_install_with_output(self, mock_Popen, mock_expanduser):
        output = mock.Mock()
        repo = freshen.Repo('repo', install_mode='install')

        repo.install(output)

        output.send.assert_has_calls([
            mock.call('Installing repository repo with command '
                      "'sudo python setup.py install'"),
            mock.call('Stdout:', 'standard output'),
            mock.call('Stderr:', 'standard error'),
        ])
        self.assertEqual(output.send.call_count, 3)
        mock_Popen.assert_called_once_with(
            ['sudo', 'python', 'setup.py', 'install'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd='/home/test/devel/src/repo')
        mock_Popen.return_value.communicate.assert_called_once_with()

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch.object(freshen.Repo, 'handle', mock.Mock(**{
        'gc.return_value': 'gc return value',
    }))
    def test_git_gc(self, mock_expanduser):
        output = mock.Mock()
        repo = freshen.Repo('repo')

        repo.git_gc(output)

        output.send.assert_called_once_with('gc return value')
        repo.handle.gc.assert_called_once_with()

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch('git.Git', return_value='computed')
    def test_handle_cached(self, mock_Git, mock_expanduser):
        repo = freshen.Repo('repo')
        repo._handle = 'cached'

        self.assertEqual(repo.handle, 'cached')
        self.assertFalse(mock_Git.called)

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch('git.Git', return_value='computed')
    def test_handle_computed(self, mock_Git, mock_expanduser):
        repo = freshen.Repo('repo')

        self.assertEqual(repo.handle, 'computed')
        mock_Git.assert_called_once_with('/home/test/devel/src/repo')


class TestOutput(unittest2.TestCase):
    def test_init(self):
        out = freshen.Output('logfile')

        self.assertEqual(out.logfile, 'logfile')
        self.assertEqual(out.log, None)

    @mock.patch('__builtin__.open', return_value='open handle')
    def test_enter(self, mock_open):
        out = freshen.Output('logfile')

        result = out.__enter__()

        self.assertEqual(result, out)
        mock_open.assert_called_once_with('logfile', 'a', 0)
        self.assertEqual(out.log, 'open handle')

    def test_exit(self):
        out = freshen.Output('logfile')
        log = mock.Mock()
        out.log = log

        out.__exit__(None, None, None)

        log.close.assert_called_once_with()
        self.assertEqual(out.log, None)

    @mock.patch.object(sys, 'stdout')
    def test_send_nolog(self, mock_stdout):
        out = freshen.Output('logfile')

        out.send(None, '', 'no trailing newline', 'two trailing newlines\n\n')

        mock_stdout.write.assert_has_calls([
            mock.call('no trailing newline\n'),
            mock.call('two trailing newlines\n\n'),
        ])
        self.assertEqual(mock_stdout.write.call_count, 2)

    @mock.patch.object(sys, 'stdout')
    def test_send_withlog(self, mock_stdout):
        out = freshen.Output('logfile')
        out.log = mock.Mock()

        out.send(None, '', 'no trailing newline', 'two trailing newlines\n\n')

        out.log.write.assert_has_calls([
            mock.call('no trailing newline\n'),
            mock.call('two trailing newlines\n\n'),
        ])
        self.assertEqual(out.log.write.call_count, 2)
        mock_stdout.write.assert_has_calls([
            mock.call('no trailing newline\n'),
            mock.call('two trailing newlines\n\n'),
        ])
        self.assertEqual(mock_stdout.write.call_count, 2)


class TestGetRepos(unittest2.TestCase):
    def make_fake_cfg(self, conf={}):
        def get(sect, opt):
            if sect not in conf:
                raise ConfigParser.NoSectionError(sect)
            elif opt not in conf[sect]:
                raise ConfigParser.NoOptionError(opt, sect)
            return conf[sect][opt]

        def sections():
            return conf.keys()

        def add_section(sect):
            if sect in conf:
                raise ConfigParser.DuplicateSectionError(sect)
            conf[sect] = {}

        def items(sect):
            if sect not in conf:
                raise ConfigParser.NoSectionError(sect)
            return conf[sect].items()

        return mock.Mock(**{
            'get.side_effect': get,
            'sections.side_effect': sections,
            'add_section.side_effect': add_section,
            'items.side_effect': items,
        })

    @mock.patch.object(freshen, 'Repo')
    def test_empty(self, mock_Repo):
        cfg = self.make_fake_cfg()

        result = freshen.get_repos(cfg)

        self.assertEqual(result, [])
        self.assertFalse(mock_Repo.called)

    @mock.patch.object(freshen, 'Repo')
    def test_from_list(self, mock_Repo):
        cfg = self.make_fake_cfg({
            'repos': {
                'list': 'repo1, repo2 , repo3,repo4,',
            },
            'repo:repo1': {
                'repo': '1',
            },
            'repo:repo2': {
                'name': '2oper',
                'repo': '2',
            },
        })

        result = freshen.get_repos(cfg)

        self.assertEqual(len(result), 4)
        mock_Repo.assert_has_calls([
            mock.call(name='repo1', repo='1'),
            mock.call(name='2oper', repo='2'),
            mock.call(name='repo3'),
            mock.call(name='repo4'),
        ], any_order=True)

    @mock.patch.object(freshen, 'Repo')
    def test_from_sections(self, mock_Repo):
        cfg = self.make_fake_cfg({
            'repo:repo1': {
                'repo': '1',
            },
            'repo:repo2': {
                'name': '2oper',
                'repo': '2',
            },
        })

        result = freshen.get_repos(cfg)

        self.assertEqual(len(result), 2)
        mock_Repo.assert_has_calls([
            mock.call(name='repo1', repo='1'),
            mock.call(name='2oper', repo='2'),
        ], any_order=True)

    @mock.patch.object(freshen, 'Repo')
    def test_from_list_restricted(self, mock_Repo):
        cfg = self.make_fake_cfg({
            'repos': {
                'list': 'repo1, repo2 , repo3,repo4,',
            },
            'repo:repo1': {
                'repo': '1',
            },
            'repo:repo2': {
                'name': '2oper',
                'repo': '2',
            },
        })

        result = freshen.get_repos(cfg, ['repo1', 'repo2', 'repo8'])

        self.assertEqual(len(result), 3)
        mock_Repo.assert_has_calls([
            mock.call(name='repo1', repo='1'),
            mock.call(name='2oper', repo='2'),
            mock.call(name='repo8'),
        ], any_order=True)


class TestPrepare(unittest2.TestCase):
    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'get.side_effect': ConfigParser.NoSectionError('repos'),
    }))
    @mock.patch.object(freshen, 'get_repos', return_value='repos')
    @mock.patch.object(freshen, 'Output', return_value='output')
    def test_logfile_nosection(self, mock_Output, mock_get_repos,
                               mock_SafeConfigParser, mock_expanduser):
        cfg = mock_SafeConfigParser.return_value

        result = freshen.prepare('~/.repos.ini', None, 'restrict')

        self.assertEqual(result, ('repos', 'output'))
        cfg.read.assert_called_once_with('/home/test/.repos.ini')
        mock_get_repos.assert_called_once_with(cfg, 'restrict')
        mock_Output.assert_called_once_with('/home/test/freshen.log')

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'get.side_effect': ConfigParser.NoOptionError('logfile', 'repos'),
    }))
    @mock.patch.object(freshen, 'get_repos', return_value='repos')
    @mock.patch.object(freshen, 'Output', return_value='output')
    def test_logfile_nooption(self, mock_Output, mock_get_repos,
                              mock_SafeConfigParser, mock_expanduser):
        cfg = mock_SafeConfigParser.return_value

        result = freshen.prepare('~/.repos.ini', None, 'restrict')

        self.assertEqual(result, ('repos', 'output'))
        cfg.read.assert_called_once_with('/home/test/.repos.ini')
        mock_get_repos.assert_called_once_with(cfg, 'restrict')
        mock_Output.assert_called_once_with('/home/test/freshen.log')

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'get.return_value': '~/my/log/file',
    }))
    @mock.patch.object(freshen, 'get_repos', return_value='repos')
    @mock.patch.object(freshen, 'Output', return_value='output')
    def test_logfile_fromconf(self, mock_Output, mock_get_repos,
                              mock_SafeConfigParser, mock_expanduser):
        cfg = mock_SafeConfigParser.return_value

        result = freshen.prepare('~/.repos.ini', None, 'restrict')

        self.assertEqual(result, ('repos', 'output'))
        cfg.read.assert_called_once_with('/home/test/.repos.ini')
        mock_get_repos.assert_called_once_with(cfg, 'restrict')
        mock_Output.assert_called_once_with('/home/test/my/log/file')

    @mock.patch('os.path.expanduser',
                side_effect=lambda x: '/home/test%s' % x[1:])
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'get.return_value': '~/my/log/file',
    }))
    @mock.patch.object(freshen, 'get_repos', return_value='repos')
    @mock.patch.object(freshen, 'Output', return_value='output')
    def test_logfile_fromargument(self, mock_Output, mock_get_repos,
                                  mock_SafeConfigParser, mock_expanduser):
        cfg = mock_SafeConfigParser.return_value

        result = freshen.prepare('~/.repos.ini', '~/arg/log', 'restrict')

        self.assertEqual(result, ('repos', 'output'))
        cfg.read.assert_called_once_with('/home/test/.repos.ini')
        mock_get_repos.assert_called_once_with(cfg, 'restrict')
        mock_Output.assert_called_once_with('/home/test/arg/log')


class TestTools(unittest2.TestCase):
    @mock.patch('datetime.datetime', mock.Mock(**{
        'now.return_value': "yyyy-mm-ddThh:mm:ss",
    }))
    @mock.patch.object(freshen, 'prepare', return_value=(
        [mock.Mock(), mock.Mock(), mock.Mock(), mock.Mock()],
        mock.MagicMock()))
    def test_freshen(self, mock_prepare):
        repos, output = mock_prepare.return_value
        for idx, repo in enumerate(repos):
            repo.name = 'repo%d' % idx

        result = freshen.freshen('repo_conf', 'logfile', 'restrict')

        self.assertEqual(result, None)
        mock_prepare.assert_called_once_with(
            'repo_conf', 'logfile', 'restrict')
        output.assert_has_calls([
            mock.call.__enter__(),
            mock.call.send("Freshening repositories at yyyy-mm-ddThh:mm:ss"),
            mock.call.send("Freshening repository repo0..."),
            mock.call.send("Freshening repository repo1..."),
            mock.call.send("Freshening repository repo2..."),
            mock.call.send("Freshening repository repo3..."),
            mock.call.__exit__(None, None, None),
        ])
        for repo in repos:
            repo.freshen.assert_called_once_with(output)

    @mock.patch('datetime.datetime', mock.Mock(**{
        'now.return_value': "yyyy-mm-ddThh:mm:ss",
    }))
    @mock.patch.object(freshen, 'prepare', return_value=(
        [mock.Mock(), mock.Mock(), mock.Mock(), mock.Mock()],
        mock.MagicMock()))
    def test_compact(self, mock_prepare):
        repos, output = mock_prepare.return_value
        for idx, repo in enumerate(repos):
            repo.name = 'repo%d' % idx

        result = freshen.compact('repo_conf', 'logfile', 'restrict')

        self.assertEqual(result, None)
        mock_prepare.assert_called_once_with(
            'repo_conf', 'logfile', 'restrict')
        output.assert_has_calls([
            mock.call.__enter__(),
            mock.call.send("Compacting repositories at yyyy-mm-ddThh:mm:ss"),
            mock.call.send("Compacting repository repo0..."),
            mock.call.send("Compacting repository repo1..."),
            mock.call.send("Compacting repository repo2..."),
            mock.call.send("Compacting repository repo3..."),
            mock.call.__exit__(None, None, None),
        ])
        for repo in repos:
            repo.git_gc.assert_called_once_with(output)
