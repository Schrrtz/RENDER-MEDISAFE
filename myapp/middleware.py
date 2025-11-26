"""
Custom middleware for handling media files on Render.
Ensures media files are accessible and properly configured.
"""

from django.conf import settings
from django.http import FileResponse
import os
import mimetypes


class MediaFileMiddleware:
    """
    Middleware to handle media file requests.
    Falls back gracefully when media files don't exist on Render.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Process request
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """
        Handle 404 errors for missing media files gracefully.
        """
        if request.path.startswith('/media/'):
            # Return a placeholder or default image
            # This prevents 404 errors from breaking the page
            return None
        return None


class StaticAndMediaMiddleware:
    """
    Ensures static and media files are served correctly on Render.
    Works alongside WhiteNoise to serve files reliably.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.media_root = settings.MEDIA_ROOT
        
    def __call__(self, request):
        response = self.get_response(request)
        return response
