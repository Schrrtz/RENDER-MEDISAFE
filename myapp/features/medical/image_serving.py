"""
Image serving and display utilities for Render deployment.
Handles media files, profile photos, and slideshows with fallback mechanisms.
"""

from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_http_methods
from django.utils.encoding import smart_str
from django.conf import settings
import os
import mimetypes
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def get_profile_photo_url(request, user_id):
    """
    Get a properly formatted profile photo URL for a user.
    Falls back to placeholder if file missing.
    """
    try:
        from myapp.models import UserProfile
        
        profile = UserProfile.objects.filter(user_id=user_id).first()
        if not profile or not profile.photo_url:
            return JsonResponse({
                'url': '/static/images/default-avatar.png',
                'exists': False
            })
        
        # Check if file exists
        if profile.photo_url.startswith('http'):
            # Already a full URL
            return JsonResponse({'url': profile.photo_url, 'exists': True})
        
        # Check if local file exists
        file_path = profile.photo_url.lstrip('/')
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        if os.path.exists(full_path):
            return JsonResponse({'url': profile.photo_url, 'exists': True})
        else:
            # File missing (ephemeral storage on Render)
            logger.warning(f"Profile photo missing for user {user_id}: {profile.photo_url}")
            return JsonResponse({
                'url': '/static/images/default-avatar.png',
                'exists': False,
                'message': 'Profile photo temporarily unavailable'
            })
    
    except Exception as e:
        logger.error(f"Error getting profile photo URL: {str(e)}")
        return JsonResponse({
            'url': '/static/images/default-avatar.png',
            'exists': False,
            'error': str(e)
        })


@require_http_methods(["GET"])
def get_media_url(request):
    """
    Check if a media file exists and return its URL or a placeholder.
    """
    try:
        file_path = request.GET.get('path', '')
        if not file_path:
            return JsonResponse({'error': 'No path provided'}, status=400)
        
        # Sanitize path
        if '..' in file_path or file_path.startswith('/'):
            return JsonResponse({'error': 'Invalid path'}, status=403)
        
        # Check if file exists
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        if os.path.exists(full_path):
            return JsonResponse({
                'url': f'/media/{file_path}',
                'exists': True
            })
        else:
            # Return placeholder based on file type
            if 'logo' in file_path.lower():
                placeholder = '/static/images/placeholder-logo.png'
            elif 'cover' in file_path.lower():
                placeholder = '/static/images/placeholder-cover.jpg'
            elif 'profile' in file_path.lower():
                placeholder = '/static/images/default-avatar.png'
            else:
                placeholder = '/static/images/placeholder.png'
            
            return JsonResponse({
                'url': placeholder,
                'exists': False,
                'message': 'File temporarily unavailable, showing placeholder'
            })
    
    except Exception as e:
        logger.error(f"Error checking media file: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def get_image_or_placeholder(image_url, image_type='profile'):
    """
    Python utility to get image URL or placeholder.
    Use in templates with: {{ image_url|get_image_or_placeholder }}
    """
    if not image_url:
        placeholders = {
            'profile': '/static/images/default-avatar.png',
            'cover': '/static/images/placeholder-cover.jpg',
            'logo': '/static/images/placeholder-logo.png',
            'default': '/static/images/placeholder.png'
        }
        return placeholders.get(image_type, placeholders['default'])
    
    # Check if URL exists
    if image_url.startswith('http'):
        return image_url
    
    # Check local file
    file_path = image_url.lstrip('/')
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    
    if os.path.exists(full_path):
        return image_url
    else:
        # Return placeholder
        placeholders = {
            'profile': '/static/images/default-avatar.png',
            'cover': '/static/images/placeholder-cover.jpg',
            'logo': '/static/images/placeholder-logo.png',
            'default': '/static/images/placeholder.png'
        }
        return placeholders.get(image_type, placeholders['default'])
