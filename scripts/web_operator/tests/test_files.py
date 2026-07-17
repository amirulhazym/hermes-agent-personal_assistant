import io
import tempfile
import unittest
from pathlib import Path

from scripts.web_operator.contracts import FileDescriptor
from scripts.web_operator.files import FileError, QuarantineStore, describe_existing_upload


class FileTests(unittest.TestCase):
    def test_two_stage_release(self):
        root = Path(tempfile.mkdtemp())
        q = QuarantineStore(root)
        expected = FileDescriptor(
            filename="note.txt",
            content_type="text/plain",
            size_bytes=5,
            sha256="",
            source="https://example.com/note.txt",
            purpose="test",
        )
        item = q.receive(expected, io.BytesIO(b"hello"))
        inspected = q.inspect(item)
        self.assertTrue(inspected.safe)
        final = q.release(inspected, approved=True)
        self.assertTrue(final.exists())

    def test_mismatch_unsafe(self):
        root = Path(tempfile.mkdtemp())
        q = QuarantineStore(root)
        expected = FileDescriptor(
            filename="note.txt",
            content_type="text/plain",
            size_bytes=5,
            sha256="deadbeef",
            source="https://example.com/note.txt",
            purpose="test",
        )
        item = q.receive(expected, io.BytesIO(b"hello"))
        inspected = q.inspect(item)
        self.assertFalse(inspected.safe)
        with self.assertRaises(FileError):
            q.release(inspected, approved=True)

    def test_describe_upload(self):
        path = Path(tempfile.mkstemp(suffix=".txt")[1])
        path.write_text("abc", encoding="utf-8")
        desc = describe_existing_upload(path, purpose="upload-test")
        self.assertEqual(desc.size_bytes, 3)
        self.assertTrue(desc.sha256)


if __name__ == "__main__":
    unittest.main()
