#! /usr/bin/env python
from setuptools import setup, find_packages, Command
from setuptools.command.test import test
import os


os.environ['DJANGO_SETTINGS_MODULE'] = 'saleor.settings'


class Test(test):
    def run(self):
        os.environ['DJANGO_SETTINGS_MODULE'] = 'saleor.settings'
        return test.run(self)


class Command(Command):
    user_options = []
    initialize_options = lambda self: None
    finalize_options = lambda self: None


class Lint(Command):
    def run(self):
        import lint
        lint.run()

setup(
    name='saleor',
    author='Mirumee Software',
    author_email='hello@mirumee.com',
    description="A fork'n'play e-commerence in Django",
    license='BSD',
    version='dev',
    url='http://getsaleor.com/',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Django>=1.5',
        'django-mptt>=0.5',
        'django-prices>=2013.1',
        'satchless>=2013.2a',
        'South>=0.7.6',
        'unidecode'],
    extras_require={
        'lint': ['pylint==0.26.0', 'django-lint==dev']},
    dependency_links=[
        'http://github.com/mirumee/satchless/tarball/django-removal#egg=satchless-2013.2a',
        'http://github.com/lamby/django-lint/tarball/master#egg=django-lint-dev'],
    entry_points={
        'console_scripts': ['saleor = saleor:manage']},
    cmdclass={
        'lint': Lint,
        'test': Test},
    tests_require=[
        'coverage==3.6',
        'mock==1.0.1',
        'nose==1.2.1'],
    test_suite='nose.collector')