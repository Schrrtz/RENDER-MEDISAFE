"""
Custom file serving views for handling media files on Render's ephemeral storage.
Provides fallback mechanisms and proper error handling.
"""

from django.http import FileResponse, JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils.encoding import smart_str
import mimetypes
import os
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def serve_media_file(request, file_path):
    """
    Serve media files with fallback handling for Render's ephemeral storage.
    """
    try:
        # Sanitize path to prevent directory traversal
        if '..' in file_path or file_path.startswith('/'):
            return JsonResponse({'error': 'Invalid file path'}, status=403)
        
        # Try to find the file
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        if not os.path.exists(full_path):
            # File doesn't exist - could be due to Render's ephemeral storage
            logger.warning(f"Media file not found: {full_path}")
            
            # Try to serve from database if it's a prescription or profile photo
            if 'prescription' in file_path:
                return JsonResponse({
                    'error': 'Prescription file not available. It may have been removed from temporary storage.',
                    'type': 'ephemeral_storage'
                }, status=410)  # 410 Gone
            
            return JsonResponse({'error': 'File not found'}, status=404)
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(full_path)
        mime_type = mime_type or 'application/octet-stream'
        
        # Serve the file
        with open(full_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=mime_type)
            filename = os.path.basename(full_path)
            response['Content-Disposition'] = f'attachment; filename="{smart_str(filename)}"'
            return response
            
    except Exception as e:
        logger.error(f"Error serving media file: {str(e)}")
        return JsonResponse({'error': f'Error serving file: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def serve_prescription_file(request, prescription_id):
    """
    Serve prescription files with database fallback.
    If file is missing, provides helpful error message about Render ephemeral storage.
    """
    from myapp.models import Prescription
    
    try:
        user_id = request.session.get('user_id') or request.session.get('user')
        if not user_id:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        
        # Get prescription
        prescription = Prescription.objects.get(prescription_id=prescription_id)
        
        if not prescription.prescription_file:
            return JsonResponse({
                'error': 'No file attached to this prescription',
                'message': 'Please ask your doctor to upload a prescription file.'
            }, status=404)
        
        # Try to serve the file
        file_obj = prescription.prescription_file
        file_name = file_obj.name.split('/')[-1]
        mime_type, _ = mimetypes.guess_type(file_name)
        
        try:
            response = FileResponse(file_obj.open('rb'), content_type=mime_type or 'application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{smart_str(file_name)}"'
            return response
        except FileNotFoundError:
            # File referenced in DB but not on disk (Render ephemeral storage issue)
            logger.warning(f"Prescription file missing: {file_obj.name}")
            return JsonResponse({
                'error': 'Prescription file not available',
                'message': 'The file has been removed from temporary storage. Please ask your doctor to re-upload it.',
                'prescription_id': prescription_id
            }, status=410)  # 410 Gone
            
    except Prescription.DoesNotExist:
        return JsonResponse({'error': 'Prescription not found'}, status=404)
    except Exception as e:
        logger.error(f"Error serving prescription: {str(e)}")
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)
