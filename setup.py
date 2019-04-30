import sys
from pathlib import Path

from setuptools import find_packages, setup
from setuptools.command.test import test as TestCommand


class Tox(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import tox
        errcode = tox.cmdline(self.test_args)
        sys.exit(errcode)


# Check if Git is present before enabling setuptools_scm
version_kwargs = {}
git_root = Path(__file__).resolve().parent / '.git'
if git_root.exists():
    version_kwargs.update({
        'use_scm_version': True,
        'setup_requires': ['setuptools_scm']
    })

setup(
    name='cardinal.py',
    **version_kwargs,
    description='A growing bot for managing a Discord server',
    author='Simon Engmann',
    author_email='simon.engmann@tu-dortmund.de',
    url='https://github.com/FallenWarrior2k/cardinal.py',
    platforms='any',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    package_data={
        'cardinal': ['db/migrations/*', 'db/migrations/**/*']
    },
    install_requires=[
        'discord.py>=1.0',
        'aiohttp',
        'SQLAlchemy>=1.3',
        'alembic',
        'lazy',
        'markdownify'
    ],
    tests_require=['tox'],
    extras_require={
        'tests': ['tox']
    },
    cmdclass={'test': Tox}
)
