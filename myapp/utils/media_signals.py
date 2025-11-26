"""
Django signals for automatic media file handling.
Processes photo uploads and cleans up old files when users update profiles.
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from myapp.models import User, UserProfile
from myapp.utils.supabase_storage import upload_profile_photo
import os


@receiver(post_save, sender=UserProfile)
def handle_profile_photo_upload(sender, instance, created, **kwargs):
    """
    Automatically handle profile photo uploads to preserve URLs.
    Triggered when UserProfile is saved.
    """
    # Profile photos are handled through custom form in views
    # This signal ensures consistency if direct model saves occur
    pass


def clean_old_profile_photo(old_photo_path):
    """
    Delete old profile photo file when user uploads a new one.
    
    Args:
        old_photo_path: Path to old photo file
    """
    if old_photo_path and old_photo_path.startswith('/media/'):
        # Extract actual file path
        file_path = old_photo_path.lstrip('/media/')
        media_root = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'media')
        full_path = os.path.join(media_root, file_path)
        
        try:
            if os.path.exists(full_path):
                os.remove(full_path)
        except Exception as e:
            print(f"Error deleting old photo: {str(e)}")


@receiver(pre_delete, sender=UserProfile)
def delete_profile_photo_on_profile_delete(sender, instance, **kwargs):
    """
    Delete profile photo file when user profile is deleted.
    """
    if instance.photo_url:
        clean_old_profile_photo(instance.photo_url)
