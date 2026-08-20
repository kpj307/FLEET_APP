import json
import logging

from django.test import SimpleTestCase

from unittest.mock import patch

from rest_framework.exceptions import (
    PermissionDenied,
    ValidationError,
)

from rest_framework.test import APIRequestFactory

from .exception_handlers import custom_exception_handler

from .audit import log_audit_event

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


class AuditLogLevelTests(SimpleTestCase):

    @patch("api.audit.audit_logger")
    def test_successful_audit_event_uses_info(
        self,
        mock_logger,
    ):
        log_audit_event(
            event="subscription.activated",
            success=True,
        )

        mock_logger.info.assert_called_once()
        mock_logger.warning.assert_not_called()

    @patch("api.audit.audit_logger")
    def test_failed_audit_event_uses_warning(
        self,
        mock_logger,
    ):
        log_audit_event(
            event="authorization.failed",
            success=False,
        )

        mock_logger.warning.assert_called_once()
        mock_logger.info.assert_not_called()


class ExceptionLogLevelTests(SimpleTestCase):

    def setUp(self):
        self.factory = APIRequestFactory()

    @patch("api.exception_handlers.logger")
    def test_client_error_uses_warning(
        self,
        mock_logger,
    ):
        request = self.factory.get(
            "/api/test/"
        )

        custom_exception_handler(
            ValidationError(
                {"field": ["Invalid value."]}
            ),
            {
                "request": request,
                "view": None,
            },
        )

        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_not_called()

    @patch("api.exception_handlers.logger")
    def test_forbidden_error_uses_warning(
        self,
        mock_logger,
    ):
        request = self.factory.get(
            "/api/protected/"
        )

        custom_exception_handler(
            PermissionDenied(
                "You do not have permission."
            ),
            {
                "request": request,
                "view": None,
            },
        )

        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_not_called()


class UnexpectedExceptionLogLevelTests(
    SimpleTestCase
):

    def setUp(self):
        self.factory = APIRequestFactory()

    @patch("api.exception_handlers.logger")
    def test_unexpected_exception_uses_error(
        self,
        mock_logger,
    ):
        request = self.factory.get(
            "/api/test/"
        )

        custom_exception_handler(
            RuntimeError(
                "Unexpected failure"
            ),
            {
                "request": request,
                "view": None,
            },
        )

        mock_logger.error.assert_called_once()
        mock_logger.warning.assert_not_called()