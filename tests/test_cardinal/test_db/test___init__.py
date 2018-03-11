import logging
import unittest as ut
import unittest.mock as mock

import cardinal.db as db


@mock.patch.object(db.Base.metadata, 'create_all')
class CreateAllTestCase(ut.TestCase):
    def test(self, create_all):
        engine = mock.NonCallableMock()

        with self.assertLogs('cardinal.db', logging.INFO):
            db.create_all(engine)

        create_all.assert_called_once_with(engine)