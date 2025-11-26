from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db import models
from django.utils import timezone
import base64
import json

from ...models import User, UserProfile, Doctor, Appointment, LabResult, LiveAppointment, Prescription
from ...models import Notification


@login_required(login_url='homepage2')
def doctor_panel(request):
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        messages.error(request, 'Unauthorized access')
        return redirect('homepage2')

    # Load related profile and doctor record if present
    try:
        profile = UserProfile.objects.get(user=user)    
    except UserProfile.DoesNotExist:
        profile = None

    try:
        doctor = Doctor.objects.select_related('user').get(user=user)
    except Doctor.DoesNotExist:
        doctor = None

    # Load this doctor's appointments (newest first)
    appointments = []
    patients = []
    today_appointments = []
    if doctor is not None:
        appointments = (
            Appointment.objects
            .select_related(
                'patient',
                'doctor',
                'doctor__user',
                'patient__userprofile'
            )
            .filter(doctor=doctor)
            .order_by('-consultation_date', '-consultation_time')
        )

        # Today's appointments (for dashboard quick view) - with proper date validation
        from django.utils import timezone as _tz
        try:
            today = _tz.now().date()
            # Only show appointments for today, not past dates
            today_appointments = appointments.filter(consultation_date=today).order_by('consultation_time')
        except Exception:
            today_appointments = []

        # Build unique patients list from appointments
        seen_patient_ids = set()
        patients_compiled = []
        for appt in appointments:
            pid = getattr(appt.patient, 'user_id', None)
            if pid and pid not in seen_patient_ids:
                seen_patient_ids.add(pid)
                try:
                    p_profile = UserProfile.objects.get(user=appt.patient)
                except UserProfile.DoesNotExist:
                    p_profile = None
                patients_compiled.append({
                    'user': appt.patient,
                    'profile': p_profile,
                    'photo_url': getattr(p_profile, 'photo_url', None) if p_profile else None,
                })
        patients = patients_compiled

    # Get all latest lab results from database
    latest_lab_results = (
        LabResult.objects
        .select_related('user', 'user__userprofile', 'uploaded_by')
        .order_by('-upload_date')[:20]  # Get latest 20 lab results
    )

    # Get all prescriptions created by this doctor
    doctor_prescriptions = []
    if doctor is not None:
        doctor_prescriptions = (
            Prescription.objects
            .select_related(
                'live_appointment',
                'live_appointment__appointment',
                'live_appointment__appointment__patient',
                'live_appointment__appointment__patient__userprofile'
            )
            .filter(live_appointment__appointment__doctor=doctor)
            .order_by('-created_at')[:50]  # Get latest 50 prescriptions
        )

    context = {
        'user': user,
        'user_profile': profile,
        'doctor': doctor,
        'appointments': appointments,
        'appointments_count': appointments.count() if hasattr(appointments, 'count') else len(appointments),
        'patients': patients,
        'latest_lab_results': latest_lab_results,
        'prescriptions': doctor_prescriptions,
        'today_appointments': today_appointments,
        'notifications': Notification.objects.filter(user=user).order_by('-created_at')[:20],
        'notif_unread_count': Notification.objects.filter(user=user, is_read=False).count(),
    }

    # Render existing static template; wire CSS/JS with correct static URLs inside template
    return render(request, 'doctors.html', context)


@login_required(login_url='homepage2')
def mark_notification_read(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
    try:
        nid = request.POST.get('notification_id')
        if not nid:
            return JsonResponse({'success': False, 'message': 'Notification id required'}, status=400)
        notif = Notification.objects.get(notification_id=nid, user=user)
        notif.is_read = True
        notif.save()
        return JsonResponse({'success': True, 'message': 'Marked as read'})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Notification not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required(login_url='homepage2')
def update_doctor_profile(request):
    if request.method != 'POST':
        return JsonResponse({"success": False, "message": "Method not allowed"}, status=405)

    user = request.user
    # Ensure only doctors can update here
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({"success": False, "message": "Unauthorized"}, status=403)

    try:
        profile, _ = UserProfile.objects.get_or_create(user=user)

        # Handle profile photo upload
        if 'profile_photo' in request.FILES:
            # Reuse logic similar to profiles.update_profile (simple manual write is fine as model has photo_url)
            from django.conf import settings
            import os
            uploaded = request.FILES['profile_photo']
            allowed_types = ['image/jpeg', 'image/png', 'image/gif']
            if uploaded.content_type not in allowed_types:
                return JsonResponse({"success": False, "message": "Invalid file type"}, status=400)
            filename = f"{user.user_id}_{uploaded.name}"
            relative_path = os.path.join('profile_photos', filename)
            full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'wb+') as destination:
                for chunk in uploaded.chunks():
                    destination.write(chunk)
            profile.photo_url = f"/media/{relative_path.replace('\\', '/')}"

        # Update profile fields
        for field in ['first_name','middle_name','last_name','sex','birthday','address','phone_number','contact_person', 'contact_number']:
            if field in request.POST:
                value = request.POST.get(field) or None
                setattr(profile, field, value)

        profile.save()

        return JsonResponse({
            "success": True,
            "message": "Profile updated successfully",
            "profile": {
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "sex": profile.sex,
                "birthday": str(profile.birthday) if profile.birthday else None,
                "address": profile.address,
                "contact_number": profile.contact_number,
                "contact_person": profile.contact_person,
                "photo": profile.photo_url.url if profile.photo_url else None,
            }
        })
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required(login_url='homepage2')
def search_patients(request):
    """AJAX endpoint for searching patients"""
    if request.method != 'GET':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({"patients": []})
    
    try:
        # Search patients by name, email, or username
        patients = (
            User.objects
            .filter(role='patient', is_active=True)
            .select_related('userprofile')
            .filter(
                models.Q(username__icontains=query) |
                models.Q(email__icontains=query) |
                models.Q(userprofile__first_name__icontains=query) |
                models.Q(userprofile__last_name__icontains=query)
            )
            .order_by('userprofile__first_name', 'userprofile__last_name', 'username')[:10]
        )
        
        patients_data = []
        for patient in patients:
            try:
                profile = patient.userprofile
                patients_data.append({
                    'user_id': patient.user_id,
                    'username': patient.username,
                    'email': patient.email,
                    'first_name': profile.first_name if profile else None,
                    'last_name': profile.last_name if profile else None,
                })
            except UserProfile.DoesNotExist:
                patients_data.append({
                    'user_id': patient.user_id,
                    'username': patient.username,
                    'email': patient.email,
                    'first_name': None,
                    'last_name': None,
                })
        
        return JsonResponse({"patients": patients_data})
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required(login_url='homepage2')
def patient_lab_results(request, patient_id):
    """AJAX endpoint for getting patient lab results"""
    if request.method != 'GET':
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        # Get the patient
        patient = User.objects.get(user_id=patient_id, role='patient', is_active=True)
        
        # Get all lab results for this patient
        lab_results = (
            LabResult.objects
            .filter(user=patient)
            .order_by('-upload_date')
        )
        
        lab_results_data = []
        for result in lab_results:
            lab_results_data.append({
                'lab_result_id': result.lab_result_id,
                'lab_type': result.lab_type,
                'file_name': result.file_name,
                'upload_date': result.upload_date.isoformat(),
                'notes': result.notes,
                'uploaded_by': result.uploaded_by.username if result.uploaded_by else 'System',
            })
        
        return JsonResponse({"lab_results": lab_results_data})
        
    except User.DoesNotExist:
        return JsonResponse({"error": "Patient not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required(login_url='homepage2')
def download_lab_result(request, result_id):
    """Download a lab result file for doctors"""
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        # Get the lab result
        lab_result = LabResult.objects.get(lab_result_id=result_id)
        
        # Decode the base64 file content
        file_content = base64.b64decode(lab_result.result_file)
        
        # Create HTTP response with file
        response = HttpResponse(file_content, content_type=lab_result.file_type)
        response['Content-Disposition'] = f'attachment; filename="{lab_result.file_name}"'
        
        return response
        
    except LabResult.DoesNotExist:
        return JsonResponse({"error": "Lab result not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required(login_url='homepage2')
def live_appointment(request):
    """Live appointment panel for doctors"""
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        messages.error(request, 'Unauthorized access')
        return redirect('homepage2')

    # Load related profile and doctor record if present
    try:
        profile = UserProfile.objects.get(user=user)    
    except UserProfile.DoesNotExist:
        profile = None

    try:
        doctor = Doctor.objects.select_related('user').get(user=user)
    except Doctor.DoesNotExist:
        doctor = None

    # Get all appointments for this doctor (not just today's)
    from django.utils import timezone
    today = timezone.now().date()
    all_appointments = []
    selected_appointment = None
    
    if doctor is not None:
        all_appointments = (
            Appointment.objects
            .select_related(
                'patient',
                'patient__userprofile'
            )
            .filter(
                doctor=doctor
            )
            .order_by('-consultation_date', 'consultation_time')
        )
        
        # Check if a specific appointment was requested
        appointment_id = request.GET.get('appointment_id')
        if appointment_id:
            try:
                selected_appointment = (
                    Appointment.objects
                    .select_related(
                        'patient',
                        'patient__userprofile'
                    )
                    .get(
                        consultation_id=appointment_id,
                        doctor=doctor
                    )
                )
            except Appointment.DoesNotExist:
                selected_appointment = None

    context = {
        'user': user,
        'user_profile': profile,
        'doctor': doctor,
        'today_appointments': all_appointments,  # Changed from today_appointments to all_appointments
        'selected_appointment': selected_appointment,
    }

    return render(request, 'live_appointment/live_appointment.html', context)


@login_required(login_url='homepage2')
def start_live_consultation(request, appointment_id):
    """Start, continue, or restart a live consultation session"""
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({'error': 'Unauthorized access'}, status=403)

    try:
        appointment = Appointment.objects.get(consultation_id=appointment_id, doctor__user=user)
        
        # Check if live session already exists
        try:
            live_session = LiveAppointment.objects.get(appointment=appointment)
            
            # Handle different session states
            if live_session.status == 'completed':
                return JsonResponse({
                    'success': True,
                    'action': 'restart',
                    'message': 'Previous session completed. Ready to restart.',
                    'live_session_id': live_session.live_appointment_id,
                    'live_session_number': getattr(live_session, 'live_appointment_number', None),
                    'previous_status': live_session.status,
                    'completed_at': live_session.completed_at.isoformat() if live_session.completed_at else None
                })
            
            elif live_session.status == 'in_progress':
                return JsonResponse({
                    'success': True,
                    'action': 'continue',
                    'message': 'Session already in progress. Ready to continue.',
                    'live_session_id': live_session.live_appointment_id,
                    'live_session_number': getattr(live_session, 'live_appointment_number', None),
                    'started_at': live_session.started_at.isoformat() if live_session.started_at else None,
                    'status': live_session.status
                })
            
            elif live_session.status in ['waiting', 'cancelled']:
                # Start the existing session
                from django.utils import timezone
                live_session.status = 'in_progress'
                live_session.started_at = timezone.now()
                live_session.save()
                
                return JsonResponse({
                    'success': True,
                    'action': 'start',
                    'message': 'Session started successfully.',
                    'live_session_id': live_session.live_appointment_id,
                    'live_session_number': getattr(live_session, 'live_appointment_number', None),
                    'started_at': live_session.started_at.isoformat(),
                    'status': live_session.status
                })
                
        except LiveAppointment.DoesNotExist:
            # Create new live appointment session
            from django.utils import timezone
            live_appointment = LiveAppointment.objects.create(
                appointment=appointment,
                status='in_progress',
                started_at=timezone.now()
            )
            
            return JsonResponse({
                'success': True,
                'action': 'start',
                'message': 'New session started successfully.',
                'live_session_id': live_appointment.live_appointment_id,
                'live_session_number': getattr(live_appointment, 'live_appointment_number', None),
                'started_at': live_appointment.started_at.isoformat(),
                'status': live_appointment.status
            })
        
    except Appointment.DoesNotExist:
        return JsonResponse({'error': 'Appointment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='homepage2')
def restart_live_consultation(request, appointment_id):
    """Restart a completed live consultation session"""
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({'error': 'Unauthorized access'}, status=403)

    try:
        appointment = Appointment.objects.get(consultation_id=appointment_id, doctor__user=user)
        
        try:
            live_session = LiveAppointment.objects.get(appointment=appointment)
            
            # Reset the session for restart
            from django.utils import timezone
            live_session.status = 'in_progress'
            live_session.started_at = timezone.now()
            live_session.completed_at = None
            live_session.session_duration = None
            # Keep existing data but allow modification
            live_session.save()
            
            return JsonResponse({
                'success': True,
                'action': 'restart',
                'message': 'Session restarted successfully.',
                'live_session_id': live_session.live_appointment_id,
                'started_at': live_session.started_at.isoformat(),
                'status': live_session.status
            })
            
        except LiveAppointment.DoesNotExist:
            return JsonResponse({'error': 'No existing session found to restart'}, status=404)
        
    except Appointment.DoesNotExist:
        return JsonResponse({'error': 'Appointment not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='homepage2')
def update_consultation_data(request, live_session_id):
    """Update or retrieve consultation data during live session"""
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({'error': 'Unauthorized access'}, status=403)

    try:
        live_session = LiveAppointment.objects.get(
            live_appointment_id=live_session_id,
            appointment__doctor__user=user
        )
        
        # Handle GET request for retrieving data
        if request.method == 'GET':
            consultation_data = {
                'symptoms': live_session.symptoms,
                'diagnosis': live_session.diagnosis,
                'clinical_notes': live_session.clinical_notes,
                'treatment_plan': live_session.treatment_plan,
                'doctor_notes': live_session.doctor_notes,
                'recommendations': live_session.recommendations,
                'vital_signs': live_session.vital_signs,
                'status': live_session.status,
                'started_at': live_session.started_at.isoformat() if live_session.started_at else None,
                'completed_at': live_session.completed_at.isoformat() if live_session.completed_at else None
            }
            return JsonResponse({
                'success': True,
                'consultation_data': consultation_data
            })
        
        # Handle POST request for updating data
        if live_session.status != 'in_progress':
            return JsonResponse({'error': 'Session not in progress'}, status=400)
        
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
        except (json.JSONDecodeError, AttributeError):
            data = request.POST
        
        # Update fields based on what's provided
        if 'vital_signs' in data:
            live_session.vital_signs = data['vital_signs']
        if 'symptoms' in data:
            live_session.symptoms = data['symptoms']
        if 'diagnosis' in data:
            live_session.diagnosis = data['diagnosis']
        if 'clinical_notes' in data:
            live_session.clinical_notes = data['clinical_notes']
        if 'treatment_plan' in data:
            live_session.treatment_plan = data['treatment_plan']
        if 'doctor_notes' in data:
            live_session.doctor_notes = data['doctor_notes']
        if 'recommendations' in data:
            live_session.recommendations = data['recommendations']
        
        live_session.save()
        
        return JsonResponse({'success': True, 'updated_at': live_session.updated_at.isoformat()})
        
    except LiveAppointment.DoesNotExist:
        return JsonResponse({'error': 'Live session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='homepage2')
def complete_consultation(request, live_session_id):
    """Complete a live consultation session"""
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({'error': 'Unauthorized access'}, status=403)

    try:
        live_session = LiveAppointment.objects.get(
            live_appointment_id=live_session_id,
            appointment__doctor__user=user
        )
        
        if live_session.status != 'in_progress':
            return JsonResponse({'error': 'Session not in progress'}, status=400)
        
        # Complete the session
        from django.utils import timezone
        live_session.status = 'completed'
        live_session.completed_at = timezone.now()
        live_session.session_duration = live_session.get_duration()
        live_session.save()
        
        # Update the original appointment status
        appointment = live_session.appointment
        appointment.status = 'Completed'
        appointment.save()
        
        return JsonResponse({
            'success': True,
            'completed_at': live_session.completed_at.isoformat(),
            'duration': live_session.session_duration
        })
        
    except LiveAppointment.DoesNotExist:
        return JsonResponse({'error': 'Live session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='homepage2')
def create_prescription(request, live_session_id):
    """Create a prescription for a completed consultation"""
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({'error': 'Unauthorized access'}, status=403)

    try:
        live_session = LiveAppointment.objects.get(
            live_appointment_id=live_session_id,
            appointment__doctor__user=user
        )
        
        if live_session.status != 'completed':
            return JsonResponse({'error': 'Consultation must be completed first'}, status=400)
        
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
        except (json.JSONDecodeError, AttributeError):
            data = request.POST
        
        prescription = Prescription.objects.create(
            live_appointment=live_session,
            medicines=data.get('medicines', []),
            instructions=data.get('instructions', ''),
            follow_up_date=data.get('follow_up_date'),
            follow_up_instructions=data.get('follow_up_instructions', ''),
            status='draft'
        )
        
        return JsonResponse({
            'success': True,
            'prescription_id': prescription.prescription_id,
            'prescription_number': prescription.prescription_number
        })
        
    except LiveAppointment.DoesNotExist:
        return JsonResponse({'error': 'Live session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='homepage2')
def sign_prescription(request, prescription_id):
    """Add digital signature to prescription"""
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({'error': 'Unauthorized access'}, status=403)

    try:
        prescription = Prescription.objects.get(
            prescription_id=prescription_id,
            live_appointment__appointment__doctor__user=user
        )
        
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
        except (json.JSONDecodeError, AttributeError):
            data = request.POST
        
        prescription.doctor_signature = data.get('signature')
        prescription.signature_date = timezone.now()
        prescription.status = 'signed'
        prescription.save()
        
        return JsonResponse({'success': True, 'signed_at': prescription.signature_date.isoformat()})
        
    except Prescription.DoesNotExist:
        return JsonResponse({'error': 'Prescription not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='homepage2')
def generate_prescription_pdf(request, prescription_id):
    """Generate PDF for prescription"""
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({'error': 'Unauthorized access'}, status=403)

    try:
        prescription = Prescription.objects.get(
            prescription_id=prescription_id,
            live_appointment__appointment__doctor__user=user
        )
        
        # Generate PDF (you'll need to implement this with reportlab or similar)
        # For now, return a placeholder response
        return JsonResponse({
            'success': True,
            'pdf_url': f'/prescriptions/{prescription_id}/pdf/',
            'message': 'PDF generation not yet implemented'
        })
        
    except Prescription.DoesNotExist:
        return JsonResponse({'error': 'Prescription not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required(login_url='homepage2')
def upload_prescription_file(request, prescription_id):
    """Upload prescription file (doctor)"""
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({'error': 'Unauthorized access'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        # Get prescription and verify ownership
        prescription = Prescription.objects.get(
            prescription_id=prescription_id,
            live_appointment__appointment__doctor__user=user
        )
        
        # Get uploaded file
        if 'prescription_file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)

        file = request.FILES['prescription_file']
        
        # Validate file type
        allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'bmp']
        file_ext = file.name.split('.')[-1].lower()
        if file_ext not in allowed_extensions:
            return JsonResponse({'error': f'File type .{file_ext} not allowed. Allowed types: {", ".join(allowed_extensions)}'}, status=400)

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if file.size > max_size:
            return JsonResponse({'error': 'File size exceeds 10MB limit'}, status=400)

        # Save file to prescription
        prescription.prescription_file = file
        prescription.save()

        return JsonResponse({
            'success': True,
            'message': 'Prescription file uploaded successfully',
            'file_name': file.name,
            'file_url': prescription.prescription_file.url if prescription.prescription_file else None
        })
        
    except Prescription.DoesNotExist:
        return JsonResponse({'error': 'Prescription not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error uploading file: {str(e)}'}, status=500)


def get_all_prescriptions(request):
    """Get all prescriptions for admin (admin only)"""
    # Check admin access via session
    user_id = request.session.get("user_id") or request.session.get("user")
    is_admin = request.session.get("is_admin", False)
    
    if not is_admin and user_id:
        try:
            user = User.objects.get(user_id=user_id)
            if user.role != 'admin':
                return JsonResponse({'error': 'Unauthorized access'}, status=403)
        except User.DoesNotExist:
            return JsonResponse({'error': 'Unauthorized access'}, status=403)
    elif not is_admin and not user_id:
        return JsonResponse({'error': 'Unauthorized access'}, status=403)

    try:
        # Get all prescriptions with related data including user profiles
        prescriptions = Prescription.objects.select_related(
            'live_appointment',
            'live_appointment__appointment',
            'live_appointment__appointment__patient',
            'live_appointment__appointment__patient__userprofile',
            'live_appointment__appointment__doctor',
            'live_appointment__appointment__doctor__user',
            'live_appointment__appointment__doctor__user__userprofile'
        ).all().order_by('-created_at')

        prescriptions_data = []
        for rx in prescriptions:
            try:
                patient = rx.live_appointment.appointment.patient
                doctor = rx.live_appointment.appointment.doctor
                
                # Get patient name from UserProfile
                patient_profile = getattr(patient, 'userprofile', None)
                if patient_profile:
                    patient_name = f"{patient_profile.first_name or ''} {patient_profile.last_name or ''}".strip()
                    if not patient_name:
                        patient_name = patient.username
                else:
                    patient_name = patient.username
                
                # Get doctor name from UserProfile
                doctor_profile = getattr(doctor.user, 'userprofile', None)
                if doctor_profile:
                    doctor_name = f"Dr. {doctor_profile.first_name or ''} {doctor_profile.last_name or ''}".strip()
                    if not doctor_name or doctor_name == "Dr. ":
                        doctor_name = f"Dr. {doctor.user.username}"
                else:
                    doctor_name = f"Dr. {doctor.user.username}"
                
                # Get medicines summary
                medicines_list = rx.medicines if rx.medicines else []
                medicines_summary = ', '.join([
                    m.get('name', '') for m in medicines_list if isinstance(m, dict) and 'name' in m
                ]) if medicines_list else ''

                prescriptions_data.append({
                    'prescription_id': rx.prescription_id,
                    'prescription_number': rx.prescription_number,
                    'patient_name': patient_name,
                    'doctor_name': doctor_name,
                    'created_at': rx.created_at.isoformat() if rx.created_at else None,
                    'status': rx.status,
                    'has_file': bool(rx.prescription_file),
                    'medicines_summary': medicines_summary[:100],  # Limit to 100 chars
                })
            except Exception as e:
                # Skip prescriptions with missing data
                import traceback
                print(f"Error processing prescription {rx.prescription_id}: {str(e)}")
                print(traceback.format_exc())
                continue

        return JsonResponse({
            'success': True,
            'prescriptions': prescriptions_data
        })
    except Exception as e:
        import traceback
        print(f"Error fetching prescriptions: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': f'Error fetching prescriptions: {str(e)}'}, status=500)


@login_required(login_url='homepage2')
def prescription_details(request, prescription_id):
    """Get prescription details as JSON for modal display"""
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        doctor = Doctor.objects.get(user=user)
        prescription = Prescription.objects.select_related(
            'live_appointment',
            'live_appointment__appointment',
            'live_appointment__appointment__patient',
            'live_appointment__appointment__patient__userprofile',
            'live_appointment__appointment__doctor',
            'live_appointment__appointment__doctor__user',
            'live_appointment__appointment__doctor__user__userprofile'
        ).get(
            prescription_id=prescription_id,
            live_appointment__appointment__doctor=doctor
        )
        
        patient = prescription.live_appointment.appointment.patient
        patient_profile = getattr(patient, 'userprofile', None)
        if patient_profile:
            patient_name = f"{patient_profile.first_name or ''} {patient_profile.last_name or ''}".strip()
            if not patient_name:
                patient_name = patient.username
        else:
            patient_name = patient.username
        
        doctor_obj = prescription.live_appointment.appointment.doctor
        doctor_profile = getattr(doctor_obj.user, 'userprofile', None)
        if doctor_profile:
            doctor_name = f"Dr. {doctor_profile.first_name or ''} {doctor_profile.last_name or ''}".strip()
            if not doctor_name or doctor_name == "Dr. ":
                doctor_name = f"Dr. {doctor_obj.user.username}"
        else:
            doctor_name = f"Dr. {doctor_obj.user.username}"
        
        return JsonResponse({
            'success': True,
            'prescription': {
                'prescription_id': prescription.prescription_id,
                'prescription_number': prescription.prescription_number,
                'patient_name': patient_name,
                'doctor_name': doctor_name,
                'status': prescription.status,
                'has_file': bool(prescription.prescription_file),
                'medicines': prescription.medicines if prescription.medicines else [],
                'created_at': prescription.created_at.isoformat() if prescription.created_at else None,
                'instructions': prescription.instructions or '',
                'follow_up_date': prescription.follow_up_date.isoformat() if prescription.follow_up_date else None,
                'follow_up_instructions': prescription.follow_up_instructions or ''
            }
        })
        
    except Prescription.DoesNotExist:
        return JsonResponse({'error': 'Prescription not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error fetching details: {str(e)}'}, status=500)


@login_required(login_url='homepage2')
def download_prescription(request, prescription_id):
    """Download prescription file"""
    user = request.user
    if getattr(user, 'role', None) != 'doctor':
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        doctor = Doctor.objects.get(user=user)
        prescription = Prescription.objects.get(
            prescription_id=prescription_id,
            live_appointment__appointment__doctor=doctor
        )
        
        if not prescription.prescription_file:
            return JsonResponse({'error': 'Prescription file not found'}, status=404)
        
        response = HttpResponse(prescription.prescription_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="prescription_{prescription.prescription_number}.pdf"'
        return response
        
    except Prescription.DoesNotExist:
        return JsonResponse({'error': 'Prescription not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error downloading file: {str(e)}'}, status=500)


