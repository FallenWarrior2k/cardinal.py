import os.path as path


def load_tests(loader, standard_tests, pattern):
    _dir = path.dirname(__file__)
    package_tests = loader.discover(start_dir=_dir, pattern=pattern)
    standard_tests.addTests(package_tests)
    return standard_tests
