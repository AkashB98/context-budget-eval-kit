import socket, unittest
import helpers  # noqa


class T(unittest.TestCase):
    def setUp(self):
        self._orig = socket.socket.connect
        socket.socket.connect = lambda *a, **k: (_ for _ in ()).throw(AssertionError("network blocked in tests except loopback serve tests"))
    def tearDown(self):
        socket.socket.connect = self._orig
    def test_pipeline_offline(self):
        from corpus import generate_corpus
        from measure import compare_all
        rows = compare_all(generate_corpus())
        self.assertEqual(len(rows), 15)
    def test_import_no_network(self):
        import compress, corpus, fidelity, measure, tokens  # noqa
        self.assertTrue(True)


if __name__ == "__main__": unittest.main()
