from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.conf import settings
import os
from django.views.decorators.csrf import csrf_exempt
import json

from ...models import (
    User,
    UserProfile,
    Patient,
    Appointment,
    Prescription,
    Notification,
    LiveAppointment,
)
from datetime import date

def userprofile(request):
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        messages.error(request, "Please login to access your profile")
        return redirect("homepage2")
    
    try:
        user = User.objects.get(user_id=user_id)
        user_profile = UserProfile.objects.get(user=user)
        patient_record = Patient.objects.filter(user=user).first()

        appointments_qs = Appointment.objects.filter(patient=user).select_related('doctor__user').order_by('-consultation_date', '-consultation_time')
        recent_appointments = list(appointments_qs[:5])
        completed_consultations = appointments_qs.filter(status='Completed').count()
        upcoming_appointments = appointments_qs.filter(status='Scheduled').count()
        total_appointments = appointments_qs.count()

        prescription_qs = Prescription.objects.filter(live_appointment__appointment__patient=user).order_by('-created_at')
        prescription_count = prescription_qs.count()
        recent_prescriptions = list(prescription_qs[:3])

        unread_notifications_count = Notification.objects.filter(user=user, is_read=False).count()

        latest_session = LiveAppointment.objects.filter(appointment__patient=user).order_by('-created_at').first()
        vitals_raw = latest_session.vital_signs if (latest_session and latest_session.vital_signs) else {}
        vital_snapshot = {
            'blood_pressure': vitals_raw.get('blood_pressure') or vitals_raw.get('bp') or '--',
            'heart_rate': vitals_raw.get('heart_rate') or vitals_raw.get('pulse') or '--',
            'glucose': vitals_raw.get('glucose') or vitals_raw.get('blood_sugar') or '--',
            'cholesterol': vitals_raw.get('cholesterol') or '--'
        }
        latest_vital_timestamp = latest_session.created_at if latest_session else None

        computed_age = None
        if user_profile.birthday:
            try:
                today = date.today()
                bd = user_profile.birthday
                computed_age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
            except Exception:
                computed_age = None

        completion_fields = [
            'first_name', 'last_name', 'birthday', 'sex',
            'address', 'contact_number', 'contact_person'
        ]
        filled_fields = sum(1 for field in completion_fields if getattr(user_profile, field, None))
        profile_completion = int((filled_fields / len(completion_fields)) * 100) if completion_fields else 0

        primary_department = appointments_qs.filter(doctor__specialization__isnull=False).values_list('doctor__specialization', flat=True).first()

        context = {
            "user": user,
            "user_profile": user_profile,
            "patient_record": patient_record,
            "recent_appointments": recent_appointments,
            "recent_prescriptions": recent_prescriptions,
            "completed_consultations": completed_consultations,
            "upcoming_appointments": upcoming_appointments,
            "total_appointments": total_appointments,
            "prescription_count": prescription_count,
            "unread_notifications_count": unread_notifications_count,
            "vital_snapshot": vital_snapshot,
            "computed_age": computed_age,
            "profile_completion": profile_completion,
            "primary_department": primary_department or 'General Medicine',
            "latest_vital_timestamp": latest_vital_timestamp,
        }
        
        return render(request, "user_profile.html", context)
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        messages.error(request, "Profile not found")
        return redirect("homepage2")

@require_http_methods(["POST"])
def update_profile_photo(request):
    """Handle profile photo upload with proper error handling"""
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    try:
        user = User.objects.get(user_id=user_id)
        user_profile = UserProfile.objects.get_or_create(user=user)[0]

        # Accept both 'photo' and 'profile_photo' keys from the form
        uploaded = request.FILES.get('photo') or request.FILES.get('profile_photo')
        if not uploaded:
            return JsonResponse({'success': False, 'error': 'No photo provided'}, status=400)

        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if uploaded.content_type not in allowed_types:
            return JsonResponse({
                'success': False, 
                'error': 'Invalid file type. Please upload a JPEG, PNG, GIF, or WebP image.'
            }, status=400)
        
        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024
        if uploaded.size > max_size:
            return JsonResponse({
                'success': False,
                'error': 'File size too large. Maximum 5MB allowed.'
            }, status=400)

        # Import storage utility
        from ...utils.supabase_storage import upload_profile_photo, clean_old_profile_photo
        import logging
        logger = logging.getLogger(__name__)

        # Delete old photo if it exists and is a string URL
        if user_profile.photo_url:
            try:
                # Ensure photo_url is a string
                photo_url_str = str(user_profile.photo_url)
                if photo_url_str and len(photo_url_str) > 0:
                    clean_old_profile_photo(photo_url_str)
                    logger.info(f"Cleaned old photo for user {user_id}")
            except Exception as cleanup_error:
                logger.warning(f"Could not clean old photo: {str(cleanup_error)}")
                # Don't fail the upload if cleanup fails

        # Upload new photo to storage
        photo_url_str = upload_profile_photo(uploaded, user.user_id)
        if not photo_url_str:
            logger.error(f"Failed to upload photo for user {user_id}")
            return JsonResponse({
                'success': False, 
                'error': 'Failed to upload photo. Please try again.'
            }, status=500)

        # Update profile URL (ensure it's a string)
        user_profile.photo_url = str(photo_url_str)
        user_profile.save()
        
        logger.info(f"Profile photo updated for user {user_id}: {photo_url_str}")

        # Create notification: account profile photo updated
        try:
            from ...models import Notification
            Notification.objects.create(
                user=user,
                title="Profile Photo Updated",
                message="Your profile photo has been updated successfully.",
                notification_type='account',
                priority='low'
            )
        except Exception as notif_error:
            logger.warning(f"Could not create notification: {str(notif_error)}")
            pass

        return JsonResponse({
            'success': True, 
            'message': 'Profile photo updated successfully!', 
            'photo_url': photo_url_str
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating profile photo: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while updating your photo. Please try again.'
        }, status=500)

@require_http_methods(["POST"])
def update_cover_photo(request):
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        return JsonResponse({'success': False, 'error': 'Not authenticated'}, status=401)

    try:
        user = User.objects.get(user_id=user_id)
        user_profile = UserProfile.objects.get_or_create(user=user)[0]
        
        if 'cover_photo' in request.FILES:
            # Delete old photo if it exists
            if user_profile.cover_photo:
                if os.path.exists(user_profile.cover_photo.path):
                    os.remove(user_profile.cover_photo.path)
            
            # Save new photo
            user_profile.cover_photo = request.FILES['cover_photo']
            user_profile.save()
            # Create notification: account cover photo updated
            try:
                from ...models import Notification
                Notification.objects.create(
                    user=user,
                    title="Cover Photo Updated",
                    message="Your cover photo has been updated successfully.",
                    notification_type='account',
                    priority='low'
                )
            except Exception:
                pass
            
            return JsonResponse({
                'success': True,
                'photo_url': user_profile.cover_photo.url
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No photo provided'
            }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["POST"])
def update_profile(request):

    try:
        user_id = request.session.get("user_id") or request.session.get("user")
        if not user_id:
            return JsonResponse({"success": False, "message": "Please login first"}, status=401)
        
        user = get_object_or_404(User, user_id=user_id)
        user_profile = get_object_or_404(UserProfile, user=user)
        
        # Handle profile photo upload if provided
        if 'photo' in request.FILES:
            uploaded = request.FILES.get('photo')
            if uploaded:
                # Validate file type
                allowed_types = ['image/jpeg', 'image/png', 'image/gif']
                if uploaded.content_type in allowed_types:
                    filename = f"{user.user_id}_{uploaded.name}"
                    relative_path = os.path.join('profile_photos', filename)
                    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
                    # Delete old photo if exists
                    if user_profile.photo_url:
                        from ...utils.supabase_storage import clean_old_profile_photo
                        clean_old_profile_photo(user_profile.photo_url)
                    
                    # Upload new photo using storage utility
                    from ...utils.supabase_storage import upload_profile_photo
                    photo_url = upload_profile_photo(uploaded, user.user_id)
                    if photo_url:
                        user_profile.photo_url = photo_url
        
        # Update UserProfile fields
        userprofile_fields = [
            'first_name', 'middle_name', 'last_name', 'birthday', 'sex', 
            'civil_status', 'address', 'contact_number', 'contact_person',
            'phone_number', 'phone_type', 'relationship_to_patient'
        ]
        for field in userprofile_fields:
            if field in request.POST:
                value = request.POST.get(field)
                setattr(user_profile, field, value or None)
        
        user_profile.save()
        
        # Update Patient fields if they exist
        patient = Patient.objects.filter(user=user).first()
        if patient:
            patient_fields = [
                'blood_type', 'allergies', 'conditions', 
                'emergency_contact_name', 'emergency_contact_phone'
            ]
            for field in patient_fields:
                if field in request.POST:
                    value = request.POST.get(field)
                    setattr(patient, field, value or None)
            
            patient.save()
        
        # Create notification
        try:
            Notification.objects.create(
                user=user,
                title="Profile Updated",
                message="Your profile was successfully updated.",
                notification_type='account',
                priority='low'
            )
        except Exception:
            pass
        
        return JsonResponse({
            "success": True,
            "message": "Profile updated successfully"
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"An error occurred: {str(e)}"
        })

@csrf_exempt
@require_http_methods(["POST"])
def update_profile_photo_legacy(request):
    """Update user's profile photo (legacy version)."""
    if not request.session.get("user"):
        return JsonResponse({"error": "Please login to update your profile photo"}, status=401)
    
    try:
        # Get the user's profile
        user_profile = UserProfile.objects.get(user_id=request.session.get("user"))
        
        if not request.FILES.get('photo'):
            return JsonResponse({"error": "No photo uploaded"}, status=400)
            
        # Handle file upload
        photo = request.FILES['photo']
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/png', 'image/gif']
        if photo.content_type not in allowed_types:
            return JsonResponse({"error": "Invalid file type. Please upload a JPEG, PNG, or GIF image."}, status=400)
            
        # Save the file path to the database
        file_path = f"profile_photos/{request.session.get('user')}_{photo.name}"
        full_path = os.path.join('media', file_path)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Save the file
        with open(full_path, 'wb+') as destination:
            for chunk in photo.chunks():
                destination.write(chunk)
        
        # Update the profile photo URL
        user_profile.photo_url = f"/media/{file_path}"
        user_profile.save()
        
        return JsonResponse({
            "message": "Profile photo updated successfully",
            "photo_url": user_profile.photo_url
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User profile not found"}, status=404)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error updating profile photo: {str(e)}")
        return JsonResponse({"error": "Failed to update profile photo"}, status=500)
