"""Document extraction rejects unreadable inputs before requesting AI."""
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED

import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject

from app.documents import DocumentError, MAX_FILE_BYTES, extract_document


def docx_bytes(text):
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('word/document.xml',
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>' + text + '</w:t></w:r></w:p></w:body></w:document>')
    return output.getvalue()


def pdf_bytes(text=None, password=None):
    writer = PdfWriter()
    page = writer.add_blank_page(612, 792)
    if text:
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
            NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): font})})
        stream = DecodedStreamObject()
        stream.set_data(f'BT /F1 12 Tf 50 700 Td ({text}) Tj ET'.encode('ascii'))
        page[NameObject('/Contents')] = stream
    if password:
        writer.encrypt(password)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_read_all_supported_formats():
    text = 'Polish manufacturing SME with 35 employees.'
    assert extract_document('project.txt', text.encode()) == text
    assert extract_document('PROJECT.DOCX', docx_bytes(text)) == text
    assert text in extract_document('project.pdf', pdf_bytes(text))


@pytest.mark.parametrize('filename,data,message', [
    ('project.exe', b'project details', 'Choose a PDF'),
    ('project.txt', b'', 'empty'),
    ('project.txt', b'X' * (MAX_FILE_BYTES + 1), 'too large'),
    ('project.txt', b'X' * 5001, '5,000'),
    ('project.txt', b'\xff\xfe\x00', 'Could not read'),
    ('project.txt', b'Hello\x00binary text', 'not readable'),
    ('project.pdf', b'not actually a pdf', 'valid PDF'),
    ('project.docx', b'not actually a docx', 'Could not read'),
    ('project.pdf', pdf_bytes(), 'no readable text'),
    ('project.pdf', pdf_bytes('Secret project text', 'password'), 'Password-protected'),
], ids=['extension', 'empty', 'file-limit', 'text-limit', 'encoding', 'binary', 'fake-pdf', 'fake-docx', 'scan', 'encrypted'])
def test_reject_invalid_documents(filename, data, message):
    with pytest.raises(DocumentError, match=message):
        extract_document(filename, data)


def test_docx_expansion_limit():
    with pytest.raises(DocumentError, match='expands'):
        extract_document('project.docx', docx_bytes('a' * (21 * 1024 * 1024)))
