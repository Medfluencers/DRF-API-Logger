"""
URL configuration for tests
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework.decorators import api_view


@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def test_api_view(request):
    """Test API view for testing middleware"""
    data = {
        'method': request.method,
        'path': request.path,
        'success': True
    }
    return JsonResponse(data)


@api_view(['GET'])
def slow_api_view(request):
    """Slow API view for testing performance filters"""
    import time
    time.sleep(0.2)  # 200ms delay
    return JsonResponse({'message': 'slow response'})


@api_view(['GET'])
def failing_api_view(request):
    """API view that raises, for testing 5xx traceback logging"""
    raise RuntimeError("boom")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/test/', test_api_view, name='test_api'),
    path('api/slow/', slow_api_view, name='slow_api'),
    path('api/fail/', failing_api_view, name='fail_api'),
    path('api/users/', test_api_view, name='user_list'),
    path('api/v1/test/', test_api_view, name='v1_test'),
]