"""Saved text/JSON round trips use only generic public model fixtures."""
import base64
import unittest

from web.report_formats import build_download, read_report_document, BEGIN_DATA, END_DATA
from web.service import EXAMPLES, analyze_document, decode_saved_upload


class ReportFormatTests(unittest.TestCase):
    def setUp(self):
        _, kind, options, text = EXAMPLES['fractional']
        self.payload = analyze_document(text, kind, options)

    def test_all_download_formats_restore_losslessly(self):
        for extension in ('txt', 'analysis', 'output'):
            with self.subTest(extension=extension):
                download = build_download(self.payload, extension)
                self.assertTrue(download['filename'].endswith('.' + extension))
                encoded = 'data:text/plain;base64,' + base64.b64encode(download['content'].encode()).decode()
                decoded = decode_saved_upload(encoded, download['filename'])
                self.assertEqual(read_report_document(decoded), self.payload['outcome'])
                self.assertEqual(analyze_document(decoded, 'saved-result'), self.payload)
        download = build_download(self.payload, 'txt')
        encoded = 'data:text/plain;base64,' + base64.b64encode(download['content'].encode()).decode()
        self.assertEqual(decode_saved_upload(encoded, 'past.txr'), download['content'])

    def test_complete_older_text_reports_recover_network_and_equations(self):
        for key in EXAMPLES:
            _, kind, options, text = EXAMPLES[key]
            original = analyze_document(text, kind, options)
            restored = analyze_document(original['report'], 'saved-result')
            self.assertEqual(restored['outcome']['deficiency'], original['outcome']['deficiency'])
            self.assertEqual(restored['outcome']['network']['complexes'], original['outcome']['network']['complexes'])
            self.assertEqual(restored['outcome']['network']['reactions'], original['outcome']['network']['reactions'])
            self.assertEqual(restored['equations'], original['equations'])
            self.assertTrue(any('older human-readable' in warning for warning in restored['outcome']['warnings']))

    def test_incomplete_summary_and_corrupted_appendix_are_rejected(self):
        for text in ('Chemical Reaction Network Deficiency Analysis\nWhole network\n  n = 2',
                     'not a report', BEGIN_DATA + '\n{}',
                     BEGIN_DATA + '\n{}\n' + END_DATA + '\nunexpected content'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                read_report_document(text)

    def test_legacy_kinetic_orders_and_parallel_reactions_are_preserved(self):
        text = 'Reactions:\nY k1-> 0\nY k2-> 0\nKinetic Orders:\nk1 = 1.4 Y\nRate Constants:\nk1=2\nk2=3'
        original = analyze_document(text, 'react')
        restored = analyze_document(original['report'], 'saved-result')
        self.assertEqual(restored['outcome']['network']['reactions'], original['outcome']['network']['reactions'])
