from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def root_view(request):
    return JsonResponse({
        "message": "Welcome to the Finance Backend API!",
        "status": "Running",
        "swagger_docs": "/api/docs/",
        "admin_panel": "/admin/"
    })

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', root_view),
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
