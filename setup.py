import os
import sys
from setuptools import setup
from setuptools.command.test import test as TestCommand

short_description = "A command line tool to help manage the antiSMASH server infrastructure."
long_description = short_description
if os.path.exists('README.rst'):
    long_description = open('README.rst').read()

install_requires = [
    'antismash_models >= 0.1.0',
    'envparse',
    'hiredis',
    'redis',
]


tests_require = [
    'pytest',
    'coverage',
    'pytest-cov',
    'pytest-mock',
    'fakeredis',
    'flake8',
    'mypy',
]


def read_version():
    for line in open(os.path.join('smashctl', '__init__.py'), 'r'):
        if line.startswith('__version__'):
            return line.split('=')[-1].strip().strip("'")


class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errcode = pytest.main(self.test_args)
        sys.exit(errcode)


setup(
    name='smashctl',
    version=read_version(),
    author='Kai Blin',
    author_email='kblin@biosustain.dtu.dk',
    description=short_description,
    long_description=long_description,
    install_requires=install_requires,
    tests_require=tests_require,
    cmdclass={'test': PyTest},
    entry_points={
        'console_scripts': [
            'smashctl=smashctl.__main__:main'
        ],
    },
    packages=['smashctl'],
    url='https://github.com/antismash/smashctl/',
    license='GNU Affero General Public License v3 or later (AGPLv3+)',
    classifiers=[
        'Programming Language :: Python',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Operating System :: OS Independent',
    ],
    extras_require={
        'testing': tests_require,
    },
)
