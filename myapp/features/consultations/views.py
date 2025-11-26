from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F, Count
from datetime import datetime
import json
import logging
from django.utils import timezone

from ...models import User, Doctor, UserProfile, Appointment, Notification

logger = logging.getLogger(__name__)

def consultations(request):
    """Client-facing consultations view for patients"""
    # Check if user is logged in
    user_id = request.session.get("user_id") or request.session.get("user")
    is_logged_in = user_id is not None
    
    try:
        # Get all doctors with their user profiles and appointment counts (optimized query)
        doctors = Doctor.objects.select_related(
            'user',
            'user__userprofile'
        ).prefetch_related(
            'doctor_consultations'  # Prefetch to avoid N+1
        ).all().annotate(
            first_name=F('user__userprofile__first_name'),
            last_name=F('user__userprofile__last_name'),
            photo_url=F('user__userprofile__photo_url'),
            appointment_count=Count('doctor_consultations')
        ).only(
            'doctor_id', 'years_of_experience', 'specialization', 'user_id',
            'user__user_id', 'user__username', 'user__role',
            'user__userprofile__first_name', 'user__userprofile__last_name',
            'user__userprofile__photo_url'
        )
        
        if is_logged_in:
            # User is logged in - show full functionality
            user = User.objects.get(user_id=user_id)
            consultations = Appointment.objects.select_related(
                'doctor',
                'doctor__user',
                'doctor__user__userprofile'
            ).filter(
                patient=user
            ).order_by('-consultation_date', '-consultation_time')
            
            return render(request, "consultations.html", {
                "user": user,
                "doctors": doctors,
                "consultations": consultations,
                "is_logged_in": True
            })
        else:
            # User is not logged in - show encouraging message and booking form
            return render(request, "consultations.html", {
                "user": None,
                "doctors": doctors,
                "consultations": [],
                "is_logged_in": False,
                "encouraging_message": "Welcome to MediSafe+! Book your appointment today and join thousands of satisfied patients who trust us with their healthcare needs."
            })
    except Exception as e:
        messages.error(request, str(e))
        return redirect("homepage2")

@csrf_exempt
@require_http_methods(["POST"])
def book_consultation(request):
    """Book a new appointment"""
    logger.info(f"Booking consultation request received")
    logger.info(f"User authenticated: {request.user.is_authenticated}")
    logger.info(f"Request user: {request.user}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"POST data keys: {list(request.POST.keys())}")
    
    # Check if user is logged in using session (this app uses custom session storage)
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        logger.warning("Unauthenticated booking attempt - no user_id in session")
        return JsonResponse({
            'status': 'error',
            'message': 'Please login to book an appointment'
        }, status=401)
    
    try:
        # Get the user from database
        try:
            user = User.objects.get(user_id=user_id)
            logger.info(f"Found user: {user.username}")
        except User.DoesNotExist:
            logger.error(f"User not found with ID: {user_id}")
            return JsonResponse({
                'status': 'error',
                'message': 'User not found'
            }, status=404)
        
        # Log incoming data
        logger.info(f"User: {user.username}, POST data: {dict(request.POST)}")
        
        # Get form data
        doctor_id = request.POST.get('doctor_id')
        consultation_type = request.POST.get('consultation_type')
        consultation_date = request.POST.get('consultation_date')
        consultation_time = request.POST.get('consultation_time')
        notes = request.POST.get('notes', '')

        # Validate required fields
        if not all([doctor_id, consultation_type, consultation_date, consultation_time]):
            logger.warning(f"Missing required fields - doctor_id:{doctor_id}, type:{consultation_type}, date:{consultation_date}, time:{consultation_time}")
            return JsonResponse({
                'status': 'error',
                'message': 'All fields are required except notes'
            }, status=400)

        # Validate consultation_type
        if consultation_type not in ['F2F', 'Tele']:
            logger.warning(f"Invalid consultation type: {consultation_type}")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid consultation type'
            }, status=400)

        # Get the doctor
        try:
            doctor = Doctor.objects.select_related('user', 'user__userprofile').get(doctor_id=doctor_id)
            logger.info(f"Found doctor: {doctor.specialization}")
        except Doctor.DoesNotExist:
            logger.error(f"Doctor not found: {doctor_id}")
            return JsonResponse({
                'status': 'error',
                'message': 'Doctor not found'
            }, status=404)

        # Check for conflicting appointments
        conflicting_appointments = Appointment.objects.filter(
            doctor=doctor,
            consultation_date=consultation_date,
            consultation_time=consultation_time,
            status__in=['Scheduled', 'Approved']
        )
        
        if conflicting_appointments.exists():
            logger.warning(f"Conflicting appointment found for {consultation_date} {consultation_time}")
            return JsonResponse({
                'status': 'error',
                'message': 'Doctor is not available at the requested time'
            }, status=400)

        # Create the appointment
        logger.info(f"Creating appointment for user {user.username}")
        consultation = Appointment.objects.create(
            patient=user,
            doctor=doctor,
            consultation_type=consultation_type,
            consultation_date=datetime.strptime(consultation_date, '%Y-%m-%d').date(),
            consultation_time=datetime.strptime(consultation_time, '%H:%M').time(),
            notes=notes,
            approval_status='Pending',
            status='Scheduled',
            duration_minutes=30,  # Default 30 minutes
            reminder_sent=False
        )
        logger.info(f"Appointment created successfully: {consultation.consultation_id}")

        # Create notification for doctor
        Notification.objects.create(
            user=doctor.user,
            title='New Appointment Request',
            message=f'New appointment request from {user.get_full_name()} for {consultation_date} at {consultation_time}',
            notification_type='appointment',
            priority='medium',
            related_id=consultation.consultation_id
        )

        # Create notification for patient
        Notification.objects.create(
            user=user,
            title='Appointment Booked',
            message=f'Your appointment with Dr. {doctor.user.userprofile.first_name} {doctor.user.userprofile.last_name} has been booked for {consultation_date} at {consultation_time}',
            notification_type='appointment',
            priority='low',
            related_id=consultation.consultation_id
        )

        logger.info("Notifications created successfully")
        
        return JsonResponse({
            'status': 'success',
            'message': f'Appointment booked successfully with Dr. {doctor.user.userprofile.first_name} {doctor.user.userprofile.last_name} for {consultation_date} at {consultation_time}',
            'consultation_id': consultation.consultation_id,
            'appointment_number': consultation.appointment_number
        })

    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'An error occurred while booking the appointment: {str(e)}'
        }, status=500)

@login_required(login_url='homepage2')
@require_http_methods(["POST"])
def cancel_consultation(request):
    """Cancel an appointment"""
    try:
        data = json.loads(request.body)
        consultation_id = data.get('consultation_id')

        if not consultation_id:
            return JsonResponse({
                'status': 'error',
                'message': 'Consultation ID is required'
            }, status=400)

        # Get the appointment and verify ownership
        try:
            consultation = Appointment.objects.get(
                consultation_id=consultation_id,
                patient=request.user  # Ensure the patient owns this consultation
            )
        except Appointment.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Appointment not found or unauthorized'
            }, status=404)

        # Check if appointment can be cancelled
        if consultation.status in ['Cancelled', 'Completed']:
            return JsonResponse({
                'status': 'error',
                'message': f'Cannot cancel an appointment that is already {consultation.status}'
            }, status=400)

        # Update the appointment status
        consultation.status = 'Cancelled'
        consultation.save()

        # TODO: Send notifications to doctor about cancellation

        return JsonResponse({
            'status': 'success',
            'message': 'Appointment cancelled successfully'
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def book_consultation_guest(request):
    """Book a new appointment for non-logged-in users"""
    try:
        # Get form data
        doctor_id = request.POST.get('doctor_id')
        consultation_type = request.POST.get('consultation_type')
        consultation_date = request.POST.get('consultation_date')
        consultation_time = request.POST.get('consultation_time')
        notes = request.POST.get('notes')
        
        # Guest user information
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        birthday = request.POST.get('birthday')
        address = request.POST.get('address')
        emergency_contact = request.POST.get('emergency_contact')
        emergency_phone = request.POST.get('emergency_phone')

        # Validate required fields
        if not all([doctor_id, consultation_type, consultation_date, consultation_time, 
                   first_name, last_name, email, phone_number, birthday]):
            return JsonResponse({
                'status': 'error',
                'message': 'All required fields must be filled'
            }, status=400)

        # Validate consultation_type
        if consultation_type not in ['F2F', 'Tele']:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid consultation type'
            }, status=400)

        # Get the doctor
        try:
            doctor = Doctor.objects.select_related('user', 'user__userprofile').get(doctor_id=doctor_id)
        except Doctor.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Doctor not found'
            }, status=404)

        # Create a temporary user for the appointment with "no account" indication
        temp_username = f"guest_no_account_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create user account for the guest
        guest_user = User.objects.create(
            username=temp_username,
            email=email,
            role='patient',
            status=True
        )
        guest_user.set_password('temp_password')  # Temporary password
        guest_user.save()
        
        # Create user profile
        UserProfile.objects.create(
            user=guest_user,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            birthday=datetime.strptime(birthday, '%Y-%m-%d').date(),
            email=email,
            phone_number=phone_number,
            address=address,
            contact_person=emergency_contact,
            contact_number=emergency_phone
        )

        # Create the appointment
        consultation = Appointment.objects.create(
            patient=guest_user,
            doctor=doctor,
            consultation_type=consultation_type,
            consultation_date=datetime.strptime(consultation_date, '%Y-%m-%d').date(),
            consultation_time=datetime.strptime(consultation_time, '%H:%M').time(),
            notes=notes,
            approval_status='Pending',
            status='Scheduled',
            duration_minutes=30,  # Default 30 minutes
            reminder_sent=False
        )

        return JsonResponse({
            'status': 'success',
            'message': f'Appointment booked successfully with Dr. {doctor.user.userprofile.first_name} {doctor.user.userprofile.last_name} for {consultation_date} at {consultation_time}. Please check your email for confirmation.',
            'consultation_id': consultation.consultation_id,
            'username': temp_username,
            'login_message': 'Your account has been created! Please login with your email and the temporary password sent to your email.'
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def create_appointment(request):
    """Create appointment for logged-in users - separate from guest booking"""
    logger.info("Create appointment request received for logged-in user")
    
    try:
        # Get the logged-in user from session
        user_id = request.session.get("user_id") or request.session.get("user")
        if not user_id:
            logger.warning("No user_id in session")
            return JsonResponse({
                'status': 'error',
                'message': 'Please login to book an appointment'
            }, status=401)
        
        # Get user from database
        try:
            user = User.objects.get(user_id=user_id)
            logger.info(f"User found: {user.username}")
        except User.DoesNotExist:
            logger.error(f"User not found: {user_id}")
            return JsonResponse({
                'status': 'error',
                'message': 'User not found'
            }, status=404)
        
        # Get form data
        doctor_id = request.POST.get('doctor_id')
        consultation_type = request.POST.get('consultation_type')
        consultation_date = request.POST.get('consultation_date')
        consultation_time = request.POST.get('consultation_time')
        notes = request.POST.get('notes', '')
        reason_for_visit = request.POST.get('reason_for_visit', '')
        
        logger.info(f"Form data received - doctor_id: {doctor_id}, type: {consultation_type}, date: {consultation_date}, time: {consultation_time}")
        
        # Validate required fields
        if not all([doctor_id, consultation_type, consultation_date, consultation_time]):
            logger.warning("Missing required fields")
            return JsonResponse({
                'status': 'error',
                'message': 'All required fields must be filled'
            }, status=400)
        
        # Validate consultation_type
        if consultation_type not in ['F2F', 'Tele']:
            logger.warning(f"Invalid consultation type: {consultation_type}")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid consultation type'
            }, status=400)
        
        # Get the doctor
        try:
            doctor = Doctor.objects.select_related('user', 'user__userprofile').get(doctor_id=doctor_id)
            logger.info(f"Doctor found: {doctor.specialization}")
        except Doctor.DoesNotExist:
            logger.error(f"Doctor not found: {doctor_id}")
            return JsonResponse({
                'status': 'error',
                'message': 'Doctor not found'
            }, status=404)
        
        # Check for conflicting appointments
        conflicting_appointments = Appointment.objects.filter(
            doctor=doctor,
            consultation_date=datetime.strptime(consultation_date, '%Y-%m-%d').date(),
            consultation_time=datetime.strptime(consultation_time, '%H:%M').time(),
            status__in=['Scheduled', 'Approved']
        )
        
        if conflicting_appointments.exists():
            logger.warning(f"Conflicting appointment found")
            return JsonResponse({
                'status': 'error',
                'message': 'Doctor is not available at the requested time'
            }, status=400)
        
        # Create the appointment
        logger.info(f"Creating appointment for user {user.username}")
        consultation = Appointment.objects.create(
            patient=user,
            doctor=doctor,
            consultation_type=consultation_type,
            consultation_date=datetime.strptime(consultation_date, '%Y-%m-%d').date(),
            consultation_time=datetime.strptime(consultation_time, '%H:%M').time(),
            notes=notes,
            reason_for_visit=reason_for_visit,
            approval_status='Pending',
            status='Scheduled',
            duration_minutes=30,
            reminder_sent=False
        )
        logger.info(f"Appointment created successfully: {consultation.consultation_id}")
        
        # Create notification for doctor
        Notification.objects.create(
            user=doctor.user,
            title='New Appointment Request',
            message=f'New appointment request from {user.get_full_name()} for {consultation_date} at {consultation_time}',
            notification_type='appointment',
            priority='medium',
            related_id=consultation.consultation_id
        )
        
        # Create notification for patient
        Notification.objects.create(
            user=user,
            title='Appointment Booked',
            message=f'Your appointment with Dr. {doctor.user.userprofile.first_name} {doctor.user.userprofile.last_name} has been booked for {consultation_date} at {consultation_time}',
            notification_type='appointment',
            priority='low',
            related_id=consultation.consultation_id
        )
        
        logger.info("Notifications created successfully")
        
        return JsonResponse({
            'status': 'success',
            'message': f'Appointment booked successfully with Dr. {doctor.user.userprofile.first_name} {doctor.user.userprofile.last_name} for {consultation_date} at {consultation_time}',
            'consultation_id': consultation.consultation_id,
            'appointment_number': consultation.appointment_number
        })
        
    except Exception as e:
        logger.error(f"Error creating appointment: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': f'An error occurred while booking the appointment: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_consultation_details(request, consultation_id):
    """Get consultation details including live appointment data for patients"""
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    
    try:
        from ...models import LiveAppointment
        user = User.objects.get(user_id=user_id)
        
        # Get the appointment
        consultation = Appointment.objects.select_related(
            'doctor', 'doctor__user', 'doctor__user__userprofile',
            'patient', 'patient__userprofile'
        ).get(consultation_id=consultation_id, patient=user)
        
        # Try to get live appointment data if exists
        live_data = {}
        try:
            live_appointment = LiveAppointment.objects.select_related('appointment').get(
                appointment=consultation
            )
            live_data = {
                'vital_signs': live_appointment.vital_signs or {},
                'symptoms': live_appointment.symptoms or '',
                'diagnosis': live_appointment.diagnosis or '',
                'clinical_notes': live_appointment.clinical_notes or '',
                'treatment_plan': live_appointment.treatment_plan or '',
                'follow_up_notes': live_appointment.follow_up_notes or '',
                'doctor_notes': live_appointment.doctor_notes or '',
                'recommendations': live_appointment.recommendations or '',
            }
        except LiveAppointment.DoesNotExist:
            pass
        
        data = {
            'consultation_id': consultation.consultation_id,
            'consultation_type': consultation.consultation_type,
            'consultation_date': consultation.consultation_date.strftime('%Y-%m-%d'),
            'consultation_time': consultation.consultation_time.strftime('%H:%M'),
            'approval_status': consultation.approval_status,
            'status': consultation.status,
            'notes': consultation.notes or '',
            'reason_for_visit': consultation.reason_for_visit or '',
            'meeting_link': consultation.meeting_link or '',
            'appointment_number': consultation.appointment_number or '',
            'doctor': f"Dr. {consultation.doctor.user.userprofile.first_name} {consultation.doctor.user.userprofile.last_name}",
            'specialization': consultation.doctor.specialization,
        }
        data.update(live_data)
        
        return JsonResponse(data)
    except Appointment.DoesNotExist:
        return JsonResponse({'error': 'Appointment not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching consultation details: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)