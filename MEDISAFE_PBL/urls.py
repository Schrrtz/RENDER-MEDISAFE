from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("myapp.urls"))
]

# Serve media files in both DEBUG and production (for Render)
if settings.DEBUG or os.getenv('RENDER'):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
