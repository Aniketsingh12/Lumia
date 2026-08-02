import pytest
from unittest.mock import patch, MagicMock


class TestRAGPipeline:
    def test_split_text(self):
        from app.utils.text_splitter import split_text

        text = "Hello world. " * 100
        chunks = split_text(text, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 150  # Allow some overflow from splitter

    def test_parse_txt(self, tmp_path):
        from app.utils.file_parser import parse_txt

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, this is a test document.")
        result = parse_txt(str(test_file))
        assert "Hello" in result
        assert "test document" in result

    def test_parse_csv(self, tmp_path):
        from app.utils.file_parser import parse_csv

        test_file = tmp_path / "test.csv"
        test_file.write_text("Name,Price\nWidget,10.99\nGadget,24.99")
        result = parse_csv(str(test_file))
        assert "Widget" in result
        assert "10.99" in result


class TestFileParser:
    def test_unsupported_type(self):
        from app.utils.file_parser import parse_file

        with pytest.raises(ValueError, match="Unsupported"):
            parse_file("test.xyz", "xyz")
