#!/usr/bin/env python

import os

from setuptools import setup


def readreq(filename):
    result = []
    with open(filename) as f:
        for req in f:
            req = req.lstrip()
            if req.startswith('-e ') or req.startswith('http:'):
                idx = req.find('#egg=')
                if idx >= 0:
                    req = req[idx + 5:].partition('#')[0].strip()
                else:
                    pass
            else:
                req = req.partition('#')[0].strip()
            if not req:
                continue
            result.append(req)
    return result


def readfile(filename):
    with open(filename) as f:
        return f.read()


setup(
    name='freshen',
    version='0.1.0',
    author='Kevin L. Mitchell',
    author_email='kevin.mitchhell@rackspace.com',
    url='https://github.com/klmitch/freshen',
    description="Tool for refreshing multiple repositories.",
    long_description=readfile('README.rst'),
    license='Apache License (2.0)',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
    ],
    py_modules=['freshen'],
    install_requires=readreq('.requires'),
    tests_require=readreq('.test-requires'),
    entry_points={
        'console_scripts': [
            'freshen = freshen:freshen.console',
            'compact = freshen:compact.console',
        ],
    },
)
