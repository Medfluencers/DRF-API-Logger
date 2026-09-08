"""
Test cases for APILoggerMiddleware
"""
import json
import os
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase, RequestFactory
from django.http import HttpResponse
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from django.test.utils import override_settings

from drf_api_logger.middleware.api_logger_middleware import APILoggerMiddleware


class TestAPILoggerMiddleware(TestCase):
    """Test cases for the API Logger Middleware"""

    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        self.middleware = APILoggerMiddleware(get_response=self.get_response)
        
    def get_response(self, request):
        """Mock get_response function"""
        response = HttpResponse(
            json.dumps({"message": "test response"}),
            content_type="application/json",
            status=200
        )
        return response

    def test_middleware_initialization(self):
        """Test middleware initializes correctly with default settings"""
        with override_settings(
            DRF_API_LOGGER_MAX_REQUEST_BODY_SIZE=32768,
            DRF_API_LOGGER_MAX_RESPONSE_BODY_SIZE=65536,
        ):
            middleware = APILoggerMiddleware(get_response=Mock())
        self.assertIsNotNone(middleware)
        self.assertEqual(middleware.DRF_API_LOGGER_PATH_TYPE, 'ABSOLUTE')
        self.assertEqual(middleware.DRF_API_LOGGER_MAX_REQUEST_BODY_SIZE, 32768)
        self.assertEqual(middleware.DRF_API_LOGGER_MAX_RESPONSE_BODY_SIZE, 65536)

    @override_settings(DRF_API_LOGGER_DATABASE=True)
    def test_middleware_with_database_enabled(self):
        """Test middleware when database logging is enabled"""
        middleware = APILoggerMiddleware(get_response=Mock())
        self.assertTrue(middleware.DRF_API_LOGGER_DATABASE)

    @override_settings(DRF_API_LOGGER_SIGNAL=True)
    def test_middleware_with_signal_enabled(self):
        """Test middleware when signal logging is enabled"""
        middleware = APILoggerMiddleware(get_response=Mock())
        self.assertTrue(middleware.DRF_API_LOGGER_SIGNAL)

    def test_static_file_request_skip(self):
        """Test that static file requests are skipped"""
        request = self.factory.get('/static/test.css')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_media_file_request_skip(self):
        """Test that media file requests are skipped"""
        request = self.factory.get('/media/test.jpg')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_admin_namespace_skip(self, mock_resolve):
        """Test that admin namespace requests are skipped"""
        mock_resolve.return_value.namespace = 'admin'
        mock_resolve.return_value.url_name = 'index'
        
        request = self.factory.get('/admin/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        DRF_API_LOGGER_DATABASE=True,
        DRF_API_LOGGER_SKIP_URL_NAME=['test_view']
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_skip_url_name(self, mock_resolve):
        """Test skipping specific URL names"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test_view'
        
        middleware = APILoggerMiddleware(get_response=self.get_response)
        request = self.factory.get('/api/test/')
        response = middleware(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        DRF_API_LOGGER_DATABASE=True,
        DRF_API_LOGGER_SKIP_NAMESPACE=['api_v1']
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_skip_namespace(self, mock_resolve):
        """Test skipping specific namespaces"""
        mock_resolve.return_value.namespace = 'api_v1'
        mock_resolve.return_value.url_name = 'list'
        
        middleware = APILoggerMiddleware(get_response=self.get_response)
        request = self.factory.get('/api/v1/users/')
        response = middleware(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        DRF_API_LOGGER_DATABASE=True,
        DRF_API_LOGGER_METHODS=['GET', 'POST']
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    @patch('drf_api_logger.apps.LOGGER_THREAD')
    def test_method_filtering(self, mock_thread, mock_resolve):
        """Test that only specified methods are logged"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'
        mock_thread.put_log_data = Mock()
        
        middleware = APILoggerMiddleware(get_response=self.get_response)
        
        # Test GET request (should be logged)
        request = self.factory.get('/api/test/')
        response = middleware(request)
        self.assertEqual(response.status_code, 200)
        
        # Test DELETE request (should not be logged)
        request = self.factory.delete('/api/test/')
        response = middleware(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        DRF_API_LOGGER_DATABASE=True,
        DRF_API_LOGGER_STATUS_CODES=[200, 201]
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    @patch('drf_api_logger.apps.LOGGER_THREAD')
    def test_status_code_filtering(self, mock_thread, mock_resolve):
        """Test that only specified status codes are logged"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'
        mock_thread.put_log_data = Mock()
        
        middleware = APILoggerMiddleware(get_response=self.get_response)
        request = self.factory.get('/api/test/')
        response = middleware(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        DRF_API_LOGGER_DATABASE=True,
        DRF_API_LOGGER_ENABLE_TRACING=True
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_tracing_enabled(self, mock_resolve):
        """Test tracing ID generation when enabled"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'
        
        middleware = APILoggerMiddleware(get_response=self.get_response)
        request = self.factory.get('/api/test/')
        response = middleware(request)
        
        self.assertTrue(hasattr(request, 'tracing_id'))
        self.assertIsNotNone(request.tracing_id)

    @override_settings(
        DRF_API_LOGGER_DATABASE=True,
        DRF_API_LOGGER_ENABLE_TRACING=True,
        DRF_API_LOGGER_TRACING_ID_HEADER_NAME='X_TRACE_ID'  # Note: HTTP_ prefix is removed by get_headers
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_tracing_from_header(self, mock_resolve):
        """Test tracing ID from request header"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'
        
        middleware = APILoggerMiddleware(get_response=self.get_response)
        request = self.factory.get('/api/test/', HTTP_X_TRACE_ID='test-trace-123')
        response = middleware(request)
        
        self.assertEqual(request.tracing_id, 'test-trace-123')

    @override_settings(
        DRF_API_LOGGER_DATABASE=True,
        DRF_API_LOGGER_MAX_REQUEST_BODY_SIZE=100
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_max_request_body_size(self, mock_resolve):
        """Test request body size limitation"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'
        
        middleware = APILoggerMiddleware(get_response=self.get_response)
        large_body = json.dumps({"data": "x" * 1000})
        request = self.factory.post('/api/test/', 
                                   data=large_body,
                                   content_type='application/json')
        response = middleware(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(
        DRF_API_LOGGER_SIGNAL=True,
        DRF_API_LOGGER_MAX_REQUEST_BODY_SIZE=20
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_request_body_truncation_marker(self, mock_resolve):
        """Test oversized request body is marked as truncated"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'

        signal_data = []
        from drf_api_logger import API_LOGGER_SIGNAL
        def listener(**kwargs):
            signal_data.append(kwargs)

        API_LOGGER_SIGNAL.listen += listener
        try:
            middleware = APILoggerMiddleware(get_response=self.get_response)
            large_body = json.dumps({"data": "x" * 100})
            request = self.factory.post(
                '/api/test/',
                data=large_body,
                content_type='application/json'
            )
            response = middleware(request)
            self.assertEqual(response.status_code, 200)
            self.assertIn('Request body truncated', signal_data[0]['body'])
        finally:
            API_LOGGER_SIGNAL.listen -= listener

    @override_settings(
        DRF_API_LOGGER_SIGNAL=True,
        DRF_API_LOGGER_MAX_RESPONSE_BODY_SIZE=20
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_response_body_truncation_marker(self, mock_resolve):
        """Test oversized response body is marked as truncated"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'

        signal_data = []
        from drf_api_logger import API_LOGGER_SIGNAL
        def listener(**kwargs):
            signal_data.append(kwargs)

        def large_response(request):
            return HttpResponse(
                json.dumps({"data": "x" * 100}),
                content_type="application/json",
                status=200
            )

        API_LOGGER_SIGNAL.listen += listener
        try:
            middleware = APILoggerMiddleware(get_response=large_response)
            request = self.factory.get('/api/test/')
            response = middleware(request)
            self.assertEqual(response.status_code, 200)
            self.assertIn('Response body truncated', signal_data[0]['response'])
        finally:
            API_LOGGER_SIGNAL.listen -= listener

    @override_settings(DRF_API_LOGGER_SIGNAL=True)
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_json_content_type_with_charset_is_logged(self, mock_resolve):
        """Test JSON responses with charset parameters are logged"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'

        signal_data = []
        from drf_api_logger import API_LOGGER_SIGNAL
        def listener(**kwargs):
            signal_data.append(kwargs)

        def charset_response(request):
            return HttpResponse(
                json.dumps({"message": "ok"}),
                content_type="application/json; charset=utf-8",
                status=200
            )

        API_LOGGER_SIGNAL.listen += listener
        try:
            middleware = APILoggerMiddleware(get_response=charset_response)
            request = self.factory.get('/api/test/')
            response = middleware(request)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(signal_data[0]['response']['message'], 'ok')
        finally:
            API_LOGGER_SIGNAL.listen -= listener

    @override_settings(
        DRF_API_LOGGER_SIGNAL=True,
        DRF_API_LOGGER_CONTENT_TYPES=['text/plain']
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_custom_text_content_type_is_logged(self, mock_resolve):
        """Test configured non-JSON content types are logged"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'

        signal_data = []
        from drf_api_logger import API_LOGGER_SIGNAL
        def listener(**kwargs):
            signal_data.append(kwargs)

        def text_response(request):
            return HttpResponse("plain response", content_type="text/plain", status=200)

        API_LOGGER_SIGNAL.listen += listener
        try:
            middleware = APILoggerMiddleware(get_response=text_response)
            request = self.factory.post(
                '/api/test/',
                data="plain request",
                content_type='text/plain'
            )
            response = middleware(request)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(signal_data[0]['body'], 'plain request')
            self.assertEqual(signal_data[0]['response'], 'plain response')
        finally:
            API_LOGGER_SIGNAL.listen -= listener

    @override_settings(
        DRF_API_LOGGER_DATABASE=False,
        DRF_API_LOGGER_SIGNAL=True,
        DRF_API_LOGGER_LOG_SERVER_ERRORS=True
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_html_server_error_is_logged_when_enabled(self, mock_resolve):
        """Test HTML 5xx responses are logged when server error logging is enabled"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'

        signal_data = []
        from drf_api_logger import API_LOGGER_SIGNAL
        def listener(**kwargs):
            signal_data.append(kwargs)

        def server_error_response(request):
            return HttpResponse(
                "<html><body>server error</body></html>",
                content_type="text/html",
                status=500
            )

        API_LOGGER_SIGNAL.listen += listener
        try:
            middleware = APILoggerMiddleware(get_response=server_error_response)
            request = self.factory.get('/api/test/')
            response = middleware(request)
            self.assertEqual(response.status_code, 500)
            self.assertEqual(len(signal_data), 1)
            self.assertEqual(signal_data[0]['status_code'], 500)
            self.assertIn('server error', signal_data[0]['response'])
        finally:
            API_LOGGER_SIGNAL.listen -= listener

    @override_settings(
        DRF_API_LOGGER_DATABASE=False,
        DRF_API_LOGGER_SIGNAL=True,
        DRF_API_LOGGER_LOG_SERVER_ERRORS=False
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_html_server_error_is_not_logged_when_disabled(self, mock_resolve):
        """Test HTML 5xx responses are skipped when server error logging is disabled"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'

        signal_data = []
        from drf_api_logger import API_LOGGER_SIGNAL
        def listener(**kwargs):
            signal_data.append(kwargs)

        def server_error_response(request):
            return HttpResponse(
                "<html><body>server error</body></html>",
                content_type="text/html",
                status=500
            )

        API_LOGGER_SIGNAL.listen += listener
        try:
            middleware = APILoggerMiddleware(get_response=server_error_response)
            request = self.factory.get('/api/test/')
            response = middleware(request)
            self.assertEqual(response.status_code, 500)
            self.assertEqual(signal_data, [])
        finally:
            API_LOGGER_SIGNAL.listen -= listener

    @override_settings(
        DRF_API_LOGGER_DATABASE=False,
        DRF_API_LOGGER_SIGNAL=True,
        DRF_API_LOGGER_LOG_SERVER_ERRORS=True
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_json_server_error_is_logged_when_enabled(self, mock_resolve):
        """Test non-HTML 5xx responses are logged when server error logging is enabled"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'

        signal_data = []
        from drf_api_logger import API_LOGGER_SIGNAL
        def listener(**kwargs):
            signal_data.append(kwargs)

        def server_error_response(request):
            return HttpResponse(
                json.dumps({"detail": "error"}),
                content_type="application/json",
                status=503
            )

        API_LOGGER_SIGNAL.listen += listener
        try:
            middleware = APILoggerMiddleware(get_response=server_error_response)
            request = self.factory.get('/api/test/')
            response = middleware(request)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(len(signal_data), 1)
            self.assertEqual(signal_data[0]['status_code'], 503)
            self.assertEqual(signal_data[0]['response']['detail'], 'error')
        finally:
            API_LOGGER_SIGNAL.listen -= listener

    @override_settings(
        DRF_API_LOGGER_DATABASE=False,
        DRF_API_LOGGER_SIGNAL=True,
        DRF_API_LOGGER_LOG_SERVER_ERRORS=True,
        DRF_API_LOGGER_STATUS_CODES=[200]
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_html_server_error_respects_status_code_filter(self, mock_resolve):
        """Test HTML 5xx logging still respects configured status code filters"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'

        signal_data = []
        from drf_api_logger import API_LOGGER_SIGNAL
        def listener(**kwargs):
            signal_data.append(kwargs)

        def server_error_response(request):
            return HttpResponse(
                "<html><body>server error</body></html>",
                content_type="text/html",
                status=500
            )

        API_LOGGER_SIGNAL.listen += listener
        try:
            middleware = APILoggerMiddleware(get_response=server_error_response)
            request = self.factory.get('/api/test/')
            response = middleware(request)
            self.assertEqual(response.status_code, 500)
            self.assertEqual(signal_data, [])
        finally:
            API_LOGGER_SIGNAL.listen -= listener

    @override_settings(
        DRF_API_LOGGER_DATABASE=False,
        DRF_API_LOGGER_SIGNAL=True,
        DRF_API_LOGGER_LOG_SERVER_ERRORS=True
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_unhandled_exception_is_logged_when_enabled(self, mock_resolve):
        """Test unhandled exceptions are recorded as 500 server errors when enabled"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'

        signal_data = []
        from drf_api_logger import API_LOGGER_SIGNAL
        def listener(**kwargs):
            signal_data.append(kwargs)

        def failing_response(request):
            raise RuntimeError("boom")

        API_LOGGER_SIGNAL.listen += listener
        try:
            middleware = APILoggerMiddleware(get_response=failing_response)
            request = self.factory.get('/api/test/')
            with self.assertRaises(RuntimeError):
                middleware(request)
            self.assertEqual(len(signal_data), 1)
            self.assertEqual(signal_data[0]['status_code'], 500)
            self.assertIn('RuntimeError', signal_data[0]['response']['error'])
            self.assertIn('boom', signal_data[0]['response']['traceback'])
        finally:
            API_LOGGER_SIGNAL.listen -= listener

    def test_server_error_logging_enabled_by_default(self):
        """Test 5xx logging is on unless a setting turns it off"""
        middleware = APILoggerMiddleware(get_response=self.get_response)
        self.assertTrue(middleware.DRF_API_LOGGER_LOG_SERVER_ERRORS)

    @override_settings(DRF_API_LOG_SERVER_ERROR=False)
    def test_legacy_server_error_setting_name_still_works(self):
        """Test the deprecated DRF_API_LOG_SERVER_ERROR name is still honoured"""
        middleware = APILoggerMiddleware(get_response=self.get_response)
        self.assertFalse(middleware.DRF_API_LOGGER_LOG_SERVER_ERRORS)

    def test_process_exception_stores_exception_on_request(self):
        """Test process_exception keeps the exception for the 5xx log and defers to Django"""
        request = self.factory.get('/api/test/')
        error = RuntimeError("boom")
        result = self.middleware.process_exception(request, error)
        self.assertIsNone(result)
        self.assertIs(request._drf_api_logger_exception, error)

    @override_settings(
        DRF_API_LOGGER_DATABASE=False,
        DRF_API_LOGGER_SIGNAL=True,
        DRF_API_LOGGER_LOG_SERVER_ERRORS=True
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_server_error_with_stored_exception_logs_traceback_when_enabled(self, mock_resolve):
        """Test a 500 produced from a view exception is logged with the traceback"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'

        signal_data = []
        from drf_api_logger import API_LOGGER_SIGNAL
        def listener(**kwargs):
            signal_data.append(kwargs)

        def django_converted_response(request):
            # What Django hands back after convert_exception_to_response
            return HttpResponse("<h1>Server Error (500)</h1>", content_type="text/html", status=500)

        API_LOGGER_SIGNAL.listen += listener
        try:
            middleware = APILoggerMiddleware(get_response=django_converted_response)
            request = self.factory.get('/api/test/')
            try:
                raise RuntimeError("boom")
            except RuntimeError as exc:
                middleware.process_exception(request, exc)
            response = middleware(request)
            self.assertEqual(response.status_code, 500)
            self.assertEqual(len(signal_data), 1)
            body = signal_data[0]['response']
            self.assertEqual(body['error'], "RuntimeError('boom')")
            self.assertIn('Traceback (most recent call last)', body['traceback'])
            self.assertIn('RuntimeError: boom', body['traceback'])
        finally:
            API_LOGGER_SIGNAL.listen -= listener

    @override_settings(
        DRF_API_LOGGER_DATABASE=False,
        DRF_API_LOGGER_SIGNAL=True,
        DRF_API_LOGGER_LOG_SERVER_ERRORS=False
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_server_error_with_stored_exception_not_logged_when_disabled(self, mock_resolve):
        """Test a stored view exception does not force a log when 5xx logging is off"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'

        signal_data = []
        from drf_api_logger import API_LOGGER_SIGNAL
        def listener(**kwargs):
            signal_data.append(kwargs)

        def django_converted_response(request):
            return HttpResponse("<h1>Server Error (500)</h1>", content_type="text/html", status=500)

        API_LOGGER_SIGNAL.listen += listener
        try:
            middleware = APILoggerMiddleware(get_response=django_converted_response)
            request = self.factory.get('/api/test/')
            middleware.process_exception(request, RuntimeError("boom"))
            response = middleware(request)
            self.assertEqual(response.status_code, 500)
            self.assertEqual(signal_data, [])
        finally:
            API_LOGGER_SIGNAL.listen -= listener

    @override_settings(
        DRF_API_LOGGER_DATABASE=False,
        DRF_API_LOGGER_SIGNAL=True,
        DRF_API_LOGGER_LOG_SERVER_ERRORS=False
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_unhandled_exception_not_logged_when_disabled(self, mock_resolve):
        """Test an exception escaping get_response is re-raised but not logged when 5xx logging is off"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'

        signal_data = []
        from drf_api_logger import API_LOGGER_SIGNAL
        def listener(**kwargs):
            signal_data.append(kwargs)

        def failing_response(request):
            raise RuntimeError("boom")

        API_LOGGER_SIGNAL.listen += listener
        try:
            middleware = APILoggerMiddleware(get_response=failing_response)
            request = self.factory.get('/api/test/')
            with self.assertRaises(RuntimeError):
                middleware(request)
            self.assertEqual(signal_data, [])
        finally:
            API_LOGGER_SIGNAL.listen -= listener

    @override_settings(DRF_API_LOGGER_MAX_RESPONSE_BODY_SIZE=200)
    def test_traceback_is_truncated_keeping_the_tail(self):
        """Test an over-limit traceback keeps its final frames and the error line"""
        middleware = APILoggerMiddleware(get_response=self.get_response)

        def deep(n):
            if n == 0:
                raise RuntimeError("boom at the bottom")
            return deep(n - 1)

        try:
            deep(25)
        except RuntimeError as exc:
            body = middleware._format_exception_body(exc)
        self.assertTrue(body['traceback'].startswith('** Traceback truncated:'))
        self.assertTrue(body['traceback'].rstrip().endswith('RuntimeError: boom at the bottom'))
        self.assertLessEqual(len(body['traceback'].encode('utf-8')), 200 + 100)

    @override_settings(DRF_API_LOGGER_MAX_RESPONSE_BODY_SIZE=50)
    def test_error_field_is_truncated_like_the_traceback(self):
        """Test a huge exception message does not bypass the body limit through the error field"""
        middleware = APILoggerMiddleware(get_response=self.get_response)
        try:
            raise RuntimeError("x" * 5000)
        except RuntimeError as exc:
            body = middleware._format_exception_body(exc)
        self.assertTrue(body['error'].startswith('** Error truncated:'))
        self.assertLessEqual(len(body['error'].encode('utf-8')), 50 + 100)

    @override_settings(DRF_API_LOGGER_MAX_RESPONSE_BODY_SIZE=0)
    def test_zero_body_limit_keeps_only_the_marker(self):
        """Test a zero limit stores the truncation marker and nothing else, like _decode_body"""
        middleware = APILoggerMiddleware(get_response=self.get_response)
        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            body = middleware._format_exception_body(exc)
        self.assertNotIn('boom', body['traceback'])
        self.assertTrue(body['traceback'].startswith('** Traceback truncated:'))

    def test_exception_with_failing_repr_is_still_logged(self):
        """Test an exception whose __repr__ raises falls back to its class name"""
        middleware = APILoggerMiddleware(get_response=self.get_response)

        class Broken(Exception):
            def __repr__(self):
                raise ValueError("no repr")

        try:
            raise Broken("boom")
        except Broken as exc:
            body = middleware._format_exception_body(exc)
        self.assertEqual(body['error'], 'Broken')
        self.assertIn('Broken', body['traceback'])

    def test_stored_exception_is_released_after_logging(self):
        """Test the request no longer references the exception once the 500 row is built"""
        request = self.factory.get('/api/test/')

        def django_converted_response(request):
            return HttpResponse("<h1>Server Error (500)</h1>", content_type="text/html", status=500)

        with patch('drf_api_logger.middleware.api_logger_middleware.resolve') as mock_resolve, \
                override_settings(DRF_API_LOGGER_SIGNAL=True, DRF_API_LOGGER_DATABASE=False):
            mock_resolve.return_value.namespace = None
            mock_resolve.return_value.url_name = 'test'
            middleware = APILoggerMiddleware(get_response=django_converted_response)
            middleware.process_exception(request, RuntimeError("boom"))
            middleware(request)
        self.assertFalse(hasattr(request, '_drf_api_logger_exception'))

    def test_traceback_masks_sensitive_query_parameters(self):
        """Test a URL with a token in the exception message is masked in the log"""
        middleware = APILoggerMiddleware(get_response=self.get_response)
        try:
            raise RuntimeError("GET https://example.com/cb?token=abc123&x=1 failed")
        except RuntimeError as exc:
            body = middleware._format_exception_body(exc)
        self.assertNotIn('abc123', body['traceback'])
        self.assertNotIn('abc123', body['error'])
        self.assertIn('x=1', body['traceback'])

    @override_settings(
        DRF_API_LOGGER_SIGNAL=True,
        DRF_API_LOGGER_ENABLE_PROFILING=True,
        DRF_API_LOGGER_PROFILING_SAMPLE_RATE=0
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_profiling_sample_rate_zero_skips_profiling(self, mock_resolve):
        """Test profiling sample rate can disable profiling capture"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'

        signal_data = []
        from drf_api_logger import API_LOGGER_SIGNAL
        def listener(**kwargs):
            signal_data.append(kwargs)

        API_LOGGER_SIGNAL.listen += listener
        try:
            middleware = APILoggerMiddleware(get_response=self.get_response)
            request = self.factory.get('/api/test/')
            response = middleware(request)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('profiling_data', signal_data[0])
        finally:
            API_LOGGER_SIGNAL.listen -= listener

    @override_settings(
        DRF_API_LOGGER_DATABASE=True,
        DRF_API_LOGGER_PATH_TYPE='FULL_PATH'
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_path_type_full_path(self, mock_resolve):
        """Test FULL_PATH path type setting"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'
        
        middleware = APILoggerMiddleware(get_response=self.get_response)
        self.assertEqual(middleware.DRF_API_LOGGER_PATH_TYPE, 'FULL_PATH')

    @override_settings(
        DRF_API_LOGGER_DATABASE=True,
        DRF_API_LOGGER_PATH_TYPE='RAW_URI'
    )
    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_path_type_raw_uri(self, mock_resolve):
        """Test RAW_URI path type setting"""
        mock_resolve.return_value.namespace = None
        mock_resolve.return_value.url_name = 'test'
        
        middleware = APILoggerMiddleware(get_response=self.get_response)
        self.assertEqual(middleware.DRF_API_LOGGER_PATH_TYPE, 'RAW_URI')

    def test_json_request_body_parsing(self):
        """Test parsing of JSON request body"""
        request = self.factory.post('/api/test/',
                                   data=json.dumps({"key": "value"}),
                                   content_type='application/json')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    def test_non_json_request_body(self):
        """Test handling of non-JSON request body"""
        request = self.factory.post('/api/test/',
                                   data="plain text data",
                                   content_type='text/plain')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)

    @patch('drf_api_logger.middleware.api_logger_middleware.resolve')
    def test_exception_in_url_resolution(self, mock_resolve):
        """Test handling of exceptions in URL resolution"""
        mock_resolve.side_effect = Exception("Resolution failed")
        
        request = self.factory.get('/api/test/')
        response = self.middleware(request)
        self.assertEqual(response.status_code, 200)
