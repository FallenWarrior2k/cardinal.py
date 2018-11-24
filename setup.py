from pathlib import Path

from setuptools import setup, find_packages

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
    install_requires=[
        'discord.py@git+https://github.com/Rapptz/discord.py@rewrite',
        'aiodns',
        'SQLAlchemy>=1.1'
    ]
)
