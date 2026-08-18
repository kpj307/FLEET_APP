import json
import logging

from django.test import SimpleTestCase

from config.logging_utils import (
    StructuredJSONFormatter,
)


class StructuredLoggingTests(
    SimpleTestCase
):

    def test_formatter_outputs_json(self):
        formatter = (
            StructuredJSONFormatter()
        )

        logger = logging.getLogger(
            "api.test"
        )

        record = logger.makeRecord(
            logger.name,
            logging.WARNING,
            __file__,
            10,
            "Test warning",
            (),
            None,
        )

        output = formatter.format(
            record
        )

        data = json.loads(output)

        self.assertEqual(
            data["level"],
            "WARNING",
        )

        self.assertEqual(
            data["logger"],
            "api.test",
        )

        self.assertEqual(
            data["message"],
            "Test warning",
        )

        self.assertIn(
            "timestamp",
            data,
        )

    def test_sensitive_fields_are_not_logged(self):
        formatter = (
            StructuredJSONFormatter()
        )

        logger = logging.getLogger(
            "api.security"
        )

        record = logger.makeRecord(
            logger.name,
            logging.WARNING,
            __file__,
            10,
            "Authentication failure",
            (),
            None,
        )

        record.password = "super-secret"
        record.token = "jwt-secret"
        record.authorization = (
            "Bearer secret-token"
        )

        output = formatter.format(
            record
        )

        self.assertNotIn(
            "super-secret",
            output,
        )

        self.assertNotIn(
            "jwt-secret",
            output,
        )

        self.assertNotIn(
            "secret-token",
            output,
        )