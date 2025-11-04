import pytest
from unittest.mock import MagicMock, patch
from app.services.document_processor import DocumentProcessor


@pytest.mark.asyncio
async def test_process_document_basic(monkeypatch):
    """Test basic PDF document processing"""
    
    processor = DocumentProcessor()

    # Create proper mock structure
    mock_page = MagicMock()
    mock_page.extract_tables.return_value = [[["A", "B"], [1, 2]]]
    mock_page.extract_text.return_value = "This is a test"
    
    # Create a proper PDF mock with context manager support
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]  # This should be a list of page objects
    
    # Mock pdfplumber.open to return a context manager
    mock_pdf_context = MagicMock()
    mock_pdf_context.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf_context.__exit__ = MagicMock(return_value=None)
    
    monkeypatch.setattr("pdfplumber.open", MagicMock(return_value=mock_pdf_context))
    
    # Mock TableParser methods
    monkeypatch.setattr("app.services.table_parser.TableParser.parse_table", 
                       MagicMock(return_value=[["A", "B"], [1, 2]]))
    monkeypatch.setattr("app.services.table_parser.TableParser.classify_table",
                       MagicMock(return_value="capital_call"))
    
    # Mock chunk text
    processor._chunk_text = MagicMock(return_value=[{
        "chunk": "This is a test", 
        "metadata": {
            "page": 1,
            "chunk_size": 14,
            "type": "text"
        }
    }])

    result = await processor.process_document("fake_path.pdf", document_id=1, fund_id=1)

    assert "tables_extracted" in result
    assert "chunks_created" in result
    assert result["tables_extracted"] == 1, f"Expected 1 table, got {result['tables_extracted']}"
    assert result["chunks_created"] == 1

def test_chunk_text_creates_chunks():
    """Test that chunking works as expected"""
    processor = DocumentProcessor()

    text_content = [
        {"page": 1, "text": "This is a test document. It should be chunked properly. " * 10}
    ]

    chunks = processor._chunk_text(text_content)

    assert isinstance(chunks, list)
    assert len(chunks) > 0
    assert "chunk" in chunks[0]
    assert "metadata" in chunks[0]
    assert "page" in chunks[0]["metadata"]