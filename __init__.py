"""
calibre_plugins.comicvine - A calibre metadata source for comicvine
"""

# import required for calibre-customize to install plugin
from source import Comicvine

if __name__ == '__main__':
    import unittest

    # unit tests
    import test_parser
    import test_ranking

    # integration tests
    import test_plugin


    def get_unit_suites():
        test_loader = unittest.TestLoader()
        return [test_loader.loadTestsFromModule(test_parser),
                test_loader.loadTestsFromModule(test_ranking)]


    def get_integration_suites():
        test_loader = unittest.TestLoader()
        return [test_loader.loadTestsFromTestCase(test_plugin.TestFileList),
                test_loader.loadTestsFromTestCase(test_plugin.TestPlugin)]


    def get_known_failing_integration_suites():
        test_loader = unittest.TestLoader()
        return [
            test_loader.loadTestsFromTestCase(test_plugin.TestFailingFileList)]


    def run_tests():
        test_runner = unittest.TextTestRunner()

        for test_suite in get_unit_suites():
            test_runner.run(test_suite)

        for test_suite in get_integration_suites():
            test_runner.run(test_suite)

        # for test_suite in get_known_failing_integration_suites():
        #     test_runner.run(test_suite)


    run_tests()
