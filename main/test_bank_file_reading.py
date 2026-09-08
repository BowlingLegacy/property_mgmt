from tempfile import TemporaryDirectory

from django.core.files.base import ContentFile
from django.test import SimpleTestCase, override_settings

from .models import FinancialUpload
from .views import read_financial_upload_rows


class BankFileReadingTests(SimpleTestCase):
    def test_bank_csv_encodings_and_repeat_reads(self):
        with TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            for encoding in ("utf-8-sig", "latin-1"):
                with self.subTest(encoding=encoding):
                    upload = FinancialUpload(name="July statement")
                    upload.file.save(
                        "july.csv",
                        ContentFile('Date,Description,Amount\r\n2026-07-01,"Café, vendor",12.50\r\n'.encode(encoding)),
                        save=False,
                    )
                    for _ in range(2):
                        sheet, headers, rows = read_financial_upload_rows(upload)
                        self.assertEqual(sheet, "CSV")
                        self.assertEqual(rows[0]["data"]["Description"], "Café, vendor")
                        self.assertEqual(rows[0]["data"]["Amount"], "12.50")
                        self.assertTrue(upload.file.closed)
