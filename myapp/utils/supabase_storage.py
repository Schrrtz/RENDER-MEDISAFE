"""
Supabase Storage utilities for handling file uploads and retrieval.
Provides functions to upload files to Supabase Storage and get public URLs.
"""

import os
from supabase import create_client
from django.core.files.uploadedfile import UploadedFile
import uuid
from datetime import datetime

# Initialize Supabase client
supabase_url = os.getenv('DB_HOST', 'aws-1-ap-southeast-1.pooler.supabase.com')
supabase_key = os.getenv('SUPABASE_KEY', '')  # You'll need to add this to environment variables

# For now, use a simpler approach with storage URL construction
SUPABASE_STORAGE_URL = f"https://{supabase_url.split('.pooler')[0]}.supabase.co/storage/v1/object/public"


def upload_profile_photo(file: UploadedFile, user_id: int) -> str:
    """
    Upload a profile photo to Supabase Storage.
    
    Args:
        file: Django UploadedFile object
        user_id: User ID for organizing files
        
    Returns:
        Public URL of the uploaded file
    """
    try:
        if not file:
            return None
            
        # Generate unique filename
        file_ext = file.name.split('.')[-1] if '.' in file.name else 'jpg'
        filename = f"user_{user_id}_{uuid.uuid4().hex}.{file_ext}"
        
        # Create bucket name if it doesn't exist
        bucket_name = 'profile-photos'
        
        # For production, you'd use:
        # supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        # supabase.storage.from_(bucket_name).upload(filename, file.read())
        # return f"{SUPABASE_STORAGE_URL}/{bucket_name}/{filename}"
        
        # For now, return local path (will be served by WhiteNoise)
        local_path = f"/media/profile_photos/{filename}"
        
        # Save file locally for storage
        media_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'media', 'profile_photos')
        os.makedirs(media_dir, exist_ok=True)
        
        file_path = os.path.join(media_dir, filename)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
                
        return local_path
        
    except Exception as e:
        print(f"Error uploading profile photo: {str(e)}")
        return None


def upload_prescription_file(file: UploadedFile, appointment_id: int) -> str:
    """
    Upload a prescription file to Supabase Storage.
    
    Args:
        file: Django UploadedFile object
        appointment_id: Appointment ID for organizing files
        
    Returns:
        Public URL of the uploaded file
    """
    try:
        if not file:
            return None
            
        # Generate unique filename
        file_ext = file.name.split('.')[-1] if '.' in file.name else 'pdf'
        filename = f"prescription_{appointment_id}_{uuid.uuid4().hex}.{file_ext}"
        
        # For now, return local path
        local_path = f"/media/prescriptions/{filename}"
        
        # Save file locally for storage
        media_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'media', 'prescriptions')
        os.makedirs(media_dir, exist_ok=True)
        
        file_path = os.path.join(media_dir, filename)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
                
        return local_path
        
    except Exception as e:
        print(f"Error uploading prescription file: {str(e)}")
        return None


def upload_notification_file(file: UploadedFile, notification_id: int) -> str:
    """
    Upload a notification attachment to Supabase Storage.
    
    Args:
        file: Django UploadedFile object
        notification_id: Notification ID for organizing files
        
    Returns:
        Public URL of the uploaded file
    """
    try:
        if not file:
            return None
            
        # Generate unique filename
        file_ext = file.name.split('.')[-1] if '.' in file.name else 'bin'
        filename = f"notification_{notification_id}_{uuid.uuid4().hex}.{file_ext}"
        
        # For now, return local path
        local_path = f"/media/notifications/{filename}"
        
        # Save file locally for storage
        media_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'media', 'notifications')
        os.makedirs(media_dir, exist_ok=True)
        
        file_path = os.path.join(media_dir, filename)
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
                
        return local_path
        
    except Exception as e:
        print(f"Error uploading notification file: {str(e)}")
        return None


def get_media_url(path: str) -> str:
    """
    Get the full public URL for a media file.
    Works for both local and Supabase Storage files.
    
    Args:
        path: File path (e.g., '/media/profile_photos/file.jpg')
        
    Returns:
        Full public URL
    """
    if not path:
        return None
        
    if path.startswith('http'):
        return path
        
    return path  # Django will serve it via /media/ URL
