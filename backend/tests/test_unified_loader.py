import os
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from config.datasets import DATASETS_CONFIG
from etl.load_csv import (
    _convert_value,
    _dataset_files,
    _header_mapping,
    load_csv,
)


class UnifiedLoaderTests(unittest.TestCase):
    def test_every_configured_dataset_has_csv(self):
        missing = {
            dataset: _dataset_files(dataset)
            for dataset in DATASETS_CONFIG
            if not _dataset_files(dataset)
        }
        self.assertEqual({}, missing)

    def test_header_mapping_is_case_insensitive(self):
        mapping = _header_mapping(
            ["NU_NOTIFIC", "DT_NOTIFIC", "SG_UF_NOT"],
            [("nu_notific", "Int64"), ("dt_notific", "Date"), ("sg_uf_not", "String")],
        )
        self.assertEqual("NU_NOTIFIC", mapping["nu_notific"])
        self.assertEqual("DT_NOTIFIC", mapping["dt_notific"])

    def test_type_conversion_handles_dates_numbers_and_nulls(self):
        self.assertEqual(date(2026, 7, 4), _convert_value("04/07/2026", "Date"))
        self.assertEqual(12, _convert_value("12.0", "Int32"))
        self.assertEqual(1.5, _convert_value("1,5", "Float64"))
        self.assertIsNone(_convert_value("", "Nullable(String)"))
        self.assertIsNone(_convert_value("01/01/1950", "Nullable(Date)"))
        self.assertEqual(date(1950, 1, 1), _convert_value("01/01/1950", "Nullable(Date32)"))

    def test_no_dataset_means_all_configured_datasets(self):
        with patch("etl.load_csv.reload_datasets") as reload_mock:
            reload_mock.return_value = {}
            load_csv()
        self.assertEqual(list(DATASETS_CONFIG.keys()), reload_mock.call_args.args[0])

    def test_dataset_argument_limits_replacement_scope(self):
        with patch("etl.load_csv.reload_datasets") as reload_mock:
            reload_mock.return_value = {}
            load_csv(dataset="leitos")
        self.assertEqual(["leitos"], reload_mock.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
