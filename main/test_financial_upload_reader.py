from types import SimpleNamespace

from django.core.files.base import ContentFile
from django.test import SimpleTestCase

from .views import read_financial_upload_rows


class FinancialUploadReaderTests(SimpleTestCase):
    def test_rogue_csv_metadata_is_skipped_before_transaction_headers(self):
        contents = (
            "Account Name : Rogue Business Checking Basic\n"
            "Account Number : 1234\n"
            "Date Range : 07/01/2026-07/31/2026\n"
            "Transaction Number,Date,Description,Memo,Amount Debit,Amount Credit,Balance,Check Number\n"
            'txn-1,07/07/2026,"Ext Withdrawal CHARTER COMM -",ONLINE PMT,-291.38,,1000.00,\n'
        )
        source_file = ContentFile(contents.encode("utf-8"), name="july.csv")
        upload = SimpleNamespace(file=source_file)

        sheet_name, headers, rows = read_financial_upload_rows(upload)

        self.assertEqual(sheet_name, "CSV")
        self.assertEqual(headers[:3], ["Transaction Number", "Date", "Description"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["row_number"], 5)
        self.assertEqual(rows[0]["data"]["Amount Debit"], "-291.38")
