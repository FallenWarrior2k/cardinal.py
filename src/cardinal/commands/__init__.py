import glob
from os.path import dirname, basename, isfile, isdir

nodes = glob.glob(dirname(__file__) + '/*')
modules = [basename(f)[:-3] for f in nodes if isfile(f) and basename(f).endswith('.py') and not basename(f).startswith('__')]
packages = [basename(f) for f in nodes if isdir(f) and isfile(f + '/__init__.py')]

__all__ = modules + packages