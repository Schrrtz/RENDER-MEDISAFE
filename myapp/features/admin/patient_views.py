from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, FileResponse, HttpResponse
from django.db import IntegrityError, transaction, models
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime
import json
import random
import base64
from ...models import User, UserProfile, Patient, LabResult, BookedService, Prescription, Appointment, Notification

def mod_patients(request):
    """Patient management view - also handles mod_records"""
    # Check for admin session first
    if request.session.get("is_admin"):
        # Get all clients for the dropdown
        clients = User.objects.filter(role='client', is_active=True)

        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'add':
                # Get form data
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                sex = request.POST.get('sex')
                date_of_birth = request.POST.get('date_of_birth')
                blood_type = request.POST.get('blood_type')
                client_id = request.POST.get('client_id')
                allergies = request.POST.get('allergies')
                conditions = request.POST.get('conditions')
                emergency_contact_name = request.POST.get('emergency_contact_name')
                emergency_contact_phone = request.POST.get('emergency_contact_phone')

                # Validate required fields
                if not all([first_name, last_name, sex, date_of_birth, client_id]):
                    messages.error(request, "Required fields are missing")
                    return redirect('mod_patients')

                try:
                    client = User.objects.get(user_id=client_id, role='client', is_active=True)

                    # Create username from first and last name
                    base_username = f"{first_name.lower()}{last_name.lower()}"
                    username = base_username
                    counter = 1
                    
                    # Ensure unique username
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1

                    # Create MRN (Medical Record Number)
                    mrn = f"MRN{datetime.now().strftime('%Y%m')}{random.randint(1000, 9999)}"
                    while Patient.objects.filter(medical_record_number=mrn).exists():
                        mrn = f"MRN{datetime.now().strftime('%Y%m')}{random.randint(1000, 9999)}"

                    # Create new patient user
                    new_user = User.objects.create(
                        username=username,
                        email=f"{username}@healthcareplus.com",  # Temporary email
                        role='patient',
                        is_active=True
                    )
                    
                    # Set a default password
                    default_password = f"Patient@{username}"
                    new_user.set_password(default_password)
                    new_user.save()

                    # Create UserProfile
                    UserProfile.objects.create(
                        user=new_user,
                        first_name=first_name,
                        last_name=last_name,
                        sex=sex,
                        birth_date=date_of_birth
                    )

                    # Create patient record
                    Patient.objects.create(
                        user=new_user,
                        client=client,
                        medical_record_number=mrn,
                        date_of_birth=date_of_birth,
                        sex=sex,
                        blood_type=blood_type,
                        allergies=allergies,
                        conditions=conditions,
                        emergency_contact_name=emergency_contact_name,
                        emergency_contact_phone=emergency_contact_phone
                    )
                    
                    messages.success(request, f"Patient {username} added successfully! Default password: {default_password}")
                except IntegrityError:
                    messages.error(request, "Username or email already exists")
                except Exception as e:
                    # Cleanup if any error occurs
                    if 'new_user' in locals():
                        new_user.delete()
                    messages.error(request, f"Error adding patient: {str(e)}")

            elif action == 'edit':
                patient_id = request.POST.get('patient_id')
                if not patient_id:
                    messages.error(request, "No patient specified for editing")
                    return redirect('mod_patients')

                try:
                    patient = User.objects.get(user_id=patient_id, role='patient')
                    
                    # Update patient fields
                    patient.is_active = request.POST.get('status') == 'active'
                    patient.save()

                    # Update or create UserProfile
                    profile, created = UserProfile.objects.get_or_create(user=patient)
                    profile.first_name = request.POST.get('first_name', profile.first_name)
                    profile.last_name = request.POST.get('last_name', profile.last_name)
                    profile.sex = request.POST.get('sex', profile.sex)
                    profile.save()

                    messages.success(request, f"Patient '{patient.username}' updated successfully!")
                except User.DoesNotExist:
                    messages.error(request, "Patient not found")
                except IntegrityError:
                    messages.error(request, "Username or email already exists")
                except Exception as e:
                    messages.error(request, f"Error updating patient: {str(e)}")

            elif action == 'delete':
                patient_id = request.POST.get('patient_id')
                if not patient_id:
                    messages.error(request, "No patient specified for deletion")
                    return redirect('mod_patients')

                try:
                    patient = User.objects.get(user_id=patient_id, role='patient')
                    username = patient.username  # Store for success message
                    patient.delete()
                    messages.success(request, f"Patient '{username}' deleted successfully!")
                except User.DoesNotExist:
                    messages.error(request, "Patient not found")
                except Exception as e:
                    messages.error(request, f"Error deleting patient: {str(e)}")

            elif action == 'toggle_status':
                patient_id = request.POST.get('patient_id')
                if not patient_id:
                    messages.error(request, "No patient specified for status toggle")
                    return redirect('mod_patients')

                try:
                    patient = User.objects.get(user_id=patient_id, role='patient')
                    patient.is_active = not patient.is_active
                    patient.save()
                    status = "activated" if patient.is_active else "deactivated"
                    messages.success(request, f"Patient '{patient.username}' {status} successfully!")
                except User.DoesNotExist:
                    messages.error(request, "Patient not found")
                except Exception as e:
                    messages.error(request, f"Error toggling patient status: {str(e)}")

            elif action == 'upload_lab_result':
                patient_id = request.POST.get('patient_id')
                lab_type = request.POST.get('lab_type')
                lab_file = request.FILES.get('lab_file')
                notes = request.POST.get('notes', '')

                if not all([patient_id, lab_type, lab_file]):
                    messages.error(request, "Please fill in all required fields")
                    return redirect('mod_patients')

                try:
                    patient = User.objects.get(user_id=patient_id, role='patient')
                    
                    # Get the current user (uploader)
                    uploader_id = request.session.get("user_id") or request.session.get("user")
                    uploader = None
                    if uploader_id:
                        try:
                            uploader = User.objects.get(user_id=uploader_id)
                        except User.DoesNotExist:
                            pass

                    # Read file content and convert to base64 for storage
                    import base64
                    file_content = lab_file.read()
                    file_base64 = base64.b64encode(file_content).decode('utf-8')
                    
                    # Create lab result record
                    LabResult.objects.create(
                        user=patient,
                        lab_type=lab_type,
                        result_file=file_base64,
                        file_type=lab_file.content_type,
                        file_name=lab_file.name,
                        uploaded_by=uploader,
                        notes=notes
                    )
                    
                    messages.success(request, f"Lab result uploaded successfully for {patient.username}!")
                except User.DoesNotExist:
                    messages.error(request, "Patient not found")
                except Exception as e:
                    messages.error(request, f"Error uploading lab result: {str(e)}")

            elif action == 'delete_lab_result':
                lab_result_id = request.POST.get('lab_result_id')
                if not lab_result_id:
                    messages.error(request, "No lab result specified for deletion")
                    return redirect('mod_patients')

                try:
                    lab_result = LabResult.objects.get(lab_result_id=lab_result_id)
                    patient_name = lab_result.user.username
                    lab_type = lab_result.lab_type
                    lab_result.delete()
                    messages.success(request, f"Lab result '{lab_type}' for {patient_name} deleted successfully!")
                except LabResult.DoesNotExist:
                    messages.error(request, "Lab result not found")
                except Exception as e:
                    messages.error(request, f"Error deleting lab result: {str(e)}")

            elif action == 'edit_lab_result':
                lab_result_id = request.POST.get('lab_result_id')
                lab_type = request.POST.get('lab_type')
                notes = request.POST.get('notes', '')

                if not lab_result_id or not lab_type:
                    messages.error(request, "Please fill in all required fields")
                    return redirect('mod_patients')

                try:
                    lab_result = LabResult.objects.get(lab_result_id=lab_result_id)
                    lab_result.lab_type = lab_type
                    lab_result.notes = notes
                    lab_result.save()
                    messages.success(request, f"Lab result updated successfully!")
                except LabResult.DoesNotExist:
                    messages.error(request, "Lab result not found")
                except Exception as e:
                    messages.error(request, f"Error updating lab result: {str(e)}")

            elif action == 'add_booked_service':
                patient_id = request.POST.get('patient_id')
                service_name = request.POST.get('service_name')
                booking_date = request.POST.get('booking_date')
                booking_time = request.POST.get('booking_time')
                status = request.POST.get('status', 'Pending')
                notes = request.POST.get('notes', '')

                if not all([patient_id, service_name, booking_date, booking_time]):
                    messages.error(request, "Please fill in all required fields")
                    return redirect('mod_patients')

                try:
                    patient = User.objects.get(user_id=patient_id, role='patient')
                    
                    booking_date_obj = datetime.strptime(booking_date, '%Y-%m-%d').date()
                    booking_time_obj = datetime.strptime(booking_time, '%H:%M').time()
                    
                    BookedService.objects.create(
                        user=patient,
                        service_name=service_name,
                        booking_date=booking_date_obj,
                        booking_time=booking_time_obj,
                        status=status,
                        notes=notes if notes else None
                    )
                    
                    messages.success(request, f"Booked service '{service_name}' created successfully for {patient.username}!")
                except User.DoesNotExist:
                    messages.error(request, "Patient not found")
                except ValueError as e:
                    messages.error(request, f"Invalid date or time format: {str(e)}")
                except Exception as e:
                    messages.error(request, f"Error creating booked service: {str(e)}")

            elif action == 'send_message':
                # Admin quick-send notification to a patient
                target_id = request.POST.get('target_id')
                title = request.POST.get('title')
                body = request.POST.get('body')
                ntype = request.POST.get('notification_type', 'system')

                if not target_id or not title or not body:
                    messages.error(request, "Please provide a recipient, title and message body")
                    return redirect('mod_records')

                try:
                    # Ensure only admin can send
                    admin_ok = request.session.get('is_admin') or (request.session.get('user') and User.objects.filter(user_id=request.session.get('user'), role='admin').exists())
                    if not admin_ok:
                        messages.error(request, "Unauthorized")
                        return redirect('mod_records')

                    recipient = User.objects.get(user_id=target_id)
                    # Prefix that it's from Medisafe Admin
                    full_message = f"From MediSafe Admin:\n\n{body}"
                    Notification.objects.create(
                        user=recipient,
                        title=title,
                        message=full_message,
                        notification_type=ntype,
                        is_read=False,
                        priority='medium'
                    )
                    messages.success(request, f"Message sent to {recipient.username}")
                except User.DoesNotExist:
                    messages.error(request, "Recipient not found")
                except Exception as e:
                    messages.error(request, f"Error sending message: {str(e)}")

            else:
                messages.error(request, "Invalid action specified")

        # Get search query
        search_query = request.GET.get('search', '')
        
        # Get all users with patient role (not just Patient model records)
        patients_query = User.objects.filter(role='patient').select_related('userprofile')
        
        # Apply search filter if provided
        if search_query:
            patients_query = patients_query.filter(
                models.Q(username__icontains=search_query) |
                models.Q(email__icontains=search_query) |
                models.Q(userprofile__first_name__icontains=search_query) |
                models.Q(userprofile__last_name__icontains=search_query) |
                models.Q(userprofile__contact_number__icontains=search_query)
            )
        
        patients = patients_query.all()
        
        # Get statistics
        total_patients = patients.count()
        active_patients = patients.filter(is_active=True).count()
        total_lab_results = LabResult.objects.count()
        
        # Get all lab results for the admin view
        all_lab_results = LabResult.objects.select_related('user', 'uploaded_by', 'user__userprofile').order_by('-upload_date')
        
        # Get all booked services
        all_booked_services = BookedService.objects.select_related('user', 'user__userprofile').order_by('-booking_date', '-booking_time')
        booked_services_total = BookedService.objects.count()
        booked_services_pending = BookedService.objects.filter(status='Pending').count()
        booked_services_confirmed = BookedService.objects.filter(status='Confirmed').count()
        booked_services_completed = BookedService.objects.filter(status='Completed').count()
        
        context = {
            'patients': patients,
            'clients': clients,
            'total_count': total_patients,
            'active_count': active_patients,
            'inactive_count': total_lab_results,
            'search_query': search_query,
            'all_lab_results': all_lab_results,
            'all_booked_services': all_booked_services,
            'booked_services_total': booked_services_total,
            'booked_services_pending': booked_services_pending,
            'booked_services_confirmed': booked_services_confirmed,
            'booked_services_completed': booked_services_completed
        }
        return render(request, "mod_records.html", context)
    
    # Check for regular admin user
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        messages.error(request, "Please login first")
        return redirect("homepage2")
    
    try:
        user = User.objects.get(user_id=user_id)
        if user.role != 'admin':
            messages.error(request, "Access denied. Admin privileges required.")
            return redirect("homepage2")

        # Get all clients for the dropdown
        clients = User.objects.filter(role='client', is_active=True)

        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'add':
                # Get form data
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                sex = request.POST.get('sex')
                date_of_birth = request.POST.get('date_of_birth')
                blood_type = request.POST.get('blood_type')
                client_id = request.POST.get('client_id')
                allergies = request.POST.get('allergies')
                conditions = request.POST.get('conditions')
                emergency_contact_name = request.POST.get('emergency_contact_name')
                emergency_contact_phone = request.POST.get('emergency_contact_phone')

                # Validate required fields
                if not all([first_name, last_name, sex, date_of_birth, client_id]):
                    messages.error(request, "Required fields are missing")
                    return redirect('mod_patients')

                try:
                    client = User.objects.get(user_id=client_id, role='client', is_active=True)

                    # Create username from first and last name
                    base_username = f"{first_name.lower()}{last_name.lower()}"
                    username = base_username
                    counter = 1
                    
                    # Ensure unique username
                    while User.objects.filter(username=username).exists():
                        username = f"{base_username}{counter}"
                        counter += 1

                    # Create MRN (Medical Record Number)
                    mrn = f"MRN{datetime.now().strftime('%Y%m')}{random.randint(1000, 9999)}"
                    while Patient.objects.filter(medical_record_number=mrn).exists():
                        mrn = f"MRN{datetime.now().strftime('%Y%m')}{random.randint(1000, 9999)}"

                    # Create new patient user
                    new_user = User.objects.create(
                        username=username,
                        email=f"{username}@healthcareplus.com",  # Temporary email
                        role='patient',
                        is_active=True
                    )
                    
                    # Set a default password
                    default_password = f"Patient@{username}"
                    new_user.set_password(default_password)
                    new_user.save()

                    # Create UserProfile
                    UserProfile.objects.create(
                        user=new_user,
                        first_name=first_name,
                        last_name=last_name,
                        sex=sex,
                        birth_date=date_of_birth
                    )

                    # Create patient record
                    Patient.objects.create(
                        user=new_user,
                        client=client,
                        medical_record_number=mrn,
                        date_of_birth=date_of_birth,
                        sex=sex,
                        blood_type=blood_type,
                        allergies=allergies,
                        conditions=conditions,
                        emergency_contact_name=emergency_contact_name,
                        emergency_contact_phone=emergency_contact_phone
                    )
                    
                    messages.success(request, f"Patient {username} added successfully! Default password: {default_password}")
                except IntegrityError:
                    messages.error(request, "Username or email already exists")
                except Exception as e:
                    # Cleanup if any error occurs
                    if 'new_user' in locals():
                        new_user.delete()
                    messages.error(request, f"Error adding patient: {str(e)}")

            elif action == 'edit':
                patient_id = request.POST.get('patient_id')
                if not patient_id:
                    messages.error(request, "No patient specified for editing")
                    return redirect('mod_patients')

                try:
                    patient = User.objects.get(user_id=patient_id, role='patient')
                    
                    # Update patient fields
                    patient.is_active = request.POST.get('status') == 'active'
                    patient.save()

                    # Update or create UserProfile
                    profile, created = UserProfile.objects.get_or_create(user=patient)
                    profile.first_name = request.POST.get('first_name', profile.first_name)
                    profile.last_name = request.POST.get('last_name', profile.last_name)
                    profile.sex = request.POST.get('sex', profile.sex)
                    profile.save()

                    messages.success(request, f"Patient '{patient.username}' updated successfully!")
                except User.DoesNotExist:
                    messages.error(request, "Patient not found")
                except IntegrityError:
                    messages.error(request, "Username or email already exists")
                except Exception as e:
                    messages.error(request, f"Error updating patient: {str(e)}")

            elif action == 'delete':
                patient_id = request.POST.get('patient_id')
                if not patient_id:
                    messages.error(request, "No patient specified for deletion")
                    return redirect('mod_patients')

                try:
                    patient = User.objects.get(user_id=patient_id, role='patient')
                    username = patient.username  # Store for success message
                    patient.delete()
                    messages.success(request, f"Patient '{username}' deleted successfully!")
                except User.DoesNotExist:
                    messages.error(request, "Patient not found")
                except Exception as e:
                    messages.error(request, f"Error deleting patient: {str(e)}")

            elif action == 'toggle_status':
                patient_id = request.POST.get('patient_id')
                if not patient_id:
                    messages.error(request, "No patient specified for status toggle")
                    return redirect('mod_patients')

                try:
                    patient = User.objects.get(user_id=patient_id, role='patient')
                    patient.is_active = not patient.is_active
                    patient.save()
                    status = "activated" if patient.is_active else "deactivated"
                    messages.success(request, f"Patient '{patient.username}' {status} successfully!")
                except User.DoesNotExist:
                    messages.error(request, "Patient not found")
                except Exception as e:
                    messages.error(request, f"Error toggling patient status: {str(e)}")

            elif action == 'upload_lab_result':
                patient_id = request.POST.get('patient_id')
                lab_type = request.POST.get('lab_type')
                lab_file = request.FILES.get('lab_file')
                notes = request.POST.get('notes', '')

                if not all([patient_id, lab_type, lab_file]):
                    messages.error(request, "Please fill in all required fields")
                    return redirect('mod_patients')

                try:
                    patient = User.objects.get(user_id=patient_id, role='patient')
                    
                    # Get the current user (uploader)
                    uploader_id = request.session.get("user_id") or request.session.get("user")
                    uploader = None
                    if uploader_id:
                        try:
                            uploader = User.objects.get(user_id=uploader_id)
                        except User.DoesNotExist:
                            pass

                    # Read file content and convert to base64 for storage
                    import base64
                    file_content = lab_file.read()
                    file_base64 = base64.b64encode(file_content).decode('utf-8')
                    
                    # Create lab result record
                    LabResult.objects.create(
                        user=patient,
                        lab_type=lab_type,
                        result_file=file_base64,
                        file_type=lab_file.content_type,
                        file_name=lab_file.name,
                        uploaded_by=uploader,
                        notes=notes
                    )
                    
                    messages.success(request, f"Lab result uploaded successfully for {patient.username}!")
                except User.DoesNotExist:
                    messages.error(request, "Patient not found")
                except Exception as e:
                    messages.error(request, f"Error uploading lab result: {str(e)}")

            elif action == 'delete_lab_result':
                lab_result_id = request.POST.get('lab_result_id')
                if not lab_result_id:
                    messages.error(request, "No lab result specified for deletion")
                    return redirect('mod_patients')

                try:
                    lab_result = LabResult.objects.get(lab_result_id=lab_result_id)
                    patient_name = lab_result.user.username
                    lab_type = lab_result.lab_type
                    lab_result.delete()
                    messages.success(request, f"Lab result '{lab_type}' for {patient_name} deleted successfully!")
                except LabResult.DoesNotExist:
                    messages.error(request, "Lab result not found")
                except Exception as e:
                    messages.error(request, f"Error deleting lab result: {str(e)}")

            else:
                messages.error(request, "Invalid action specified")

        # Get search query
        search_query = request.GET.get('search', '')
        
        # Get all users with patient role (not just Patient model records)
        patients_query = User.objects.filter(role='patient').select_related('userprofile')
        
        # Apply search filter if provided
        if search_query:
            patients_query = patients_query.filter(
                models.Q(username__icontains=search_query) |
                models.Q(email__icontains=search_query) |
                models.Q(userprofile__first_name__icontains=search_query) |
                models.Q(userprofile__last_name__icontains=search_query) |
                models.Q(userprofile__contact_number__icontains=search_query)
            )
        
        patients = patients_query.all()
        
        # Get statistics
        total_patients = patients.count()
        active_patients = patients.filter(is_active=True).count()
        total_lab_results = LabResult.objects.count()
        
        # Get all lab results for the admin view
        all_lab_results = LabResult.objects.select_related('user', 'uploaded_by', 'user__userprofile').order_by('-upload_date')
        
        # Get all booked services
        all_booked_services = BookedService.objects.select_related('user', 'user__userprofile').order_by('-booking_date', '-booking_time')
        booked_services_total = BookedService.objects.count()
        booked_services_pending = BookedService.objects.filter(status='Pending').count()
        booked_services_confirmed = BookedService.objects.filter(status='Confirmed').count()
        booked_services_completed = BookedService.objects.filter(status='Completed').count()
        
        context = {
            'patients': patients,
            'clients': clients,
            'total_count': total_patients,
            'active_count': active_patients,
            'inactive_count': total_lab_results,
            'search_query': search_query,
            'all_lab_results': all_lab_results,
            'all_booked_services': all_booked_services,
            'booked_services_total': booked_services_total,
            'booked_services_pending': booked_services_pending,
            'booked_services_confirmed': booked_services_confirmed,
            'booked_services_completed': booked_services_completed
        }

    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect("homepage2")
        
    return render(request, "mod_records.html", context)

@csrf_exempt
@require_http_methods(["POST"])
def update_booked_service(request):
    """Update a booked service (status or full update)"""
    if not (request.session.get("is_admin") or 
            User.objects.filter(user_id=request.session.get("user"), role="admin").exists()):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        data = json.loads(request.body)
        booking_id = data.get('booking_id')
        
        if not booking_id:
            return JsonResponse({"error": "Booking ID is required"}, status=400)

        try:
            booking = BookedService.objects.get(booking_id=booking_id)
        except BookedService.DoesNotExist:
            return JsonResponse({"error": "Booked service not found"}, status=404)

        # Update status if provided
        if 'status' in data:
            booking.status = data['status']
        
        # Update other fields if provided
        if 'service_name' in data:
            booking.service_name = data['service_name']
        if 'booking_date' in data:
            booking.booking_date = data['booking_date']
        if 'booking_time' in data:
            booking.booking_time = data['booking_time']
        if 'notes' in data:
            booking.notes = data.get('notes', '')
        
        booking.updated_at = timezone.now()
        booking.save()

        return JsonResponse({
            "success": True,
            "message": "Booked service updated successfully",
            "booking_id": booking_id
        })

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_booked_service(request):
    """Delete a booked service"""
    if not (request.session.get("is_admin") or 
            User.objects.filter(user_id=request.session.get("user"), role="admin").exists()):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        if not request.body:
            return JsonResponse({"error": "Request body is empty"}, status=400)

        data = json.loads(request.body)
        booking_id = data.get('booking_id')
        
        if not booking_id:
            return JsonResponse({"error": "Booking ID is required"}, status=400)

        try:
            booking = BookedService.objects.get(booking_id=booking_id)
            booking.delete()
            return JsonResponse({
                "success": True,
                "message": "Booked service deleted successfully",
                "booking_id": booking_id
            })
        except BookedService.DoesNotExist:
            return JsonResponse({"error": "Booked service not found"}, status=404)
            
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_patient_stats(request, patient_id):
    """Get patient statistics including appointment and services count"""
    # Check admin access
    if not (request.session.get("is_admin") or 
            User.objects.filter(user_id=request.session.get("user"), role="admin").exists()):
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        # Get appointments count
        appointments_count = Appointment.objects.filter(patient_id=patient_id).count()
        
        # Get booked services count
        services_count = BookedService.objects.filter(patient_id=patient_id).count()
        
        return JsonResponse({
            "appointments_count": appointments_count,
            "services_count": services_count
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def admin_prescription_download(request, prescription_id):
    """Admin endpoint to download prescription file directly"""
    # Check admin access
    if not (request.session.get("is_admin") or 
            User.objects.filter(user_id=request.session.get("user"), role="admin").exists()):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        prescription = Prescription.objects.get(prescription_id=prescription_id)
        
        # Check if prescription has a file
        if not prescription.prescription_file:
            return JsonResponse({
                'error': 'No file attached to this prescription. Please upload a prescription file first.'
            }, status=404)
        
        # Serve the file
        response = FileResponse(prescription.prescription_file.open('rb'))
        # Get filename from prescription_file.name or create one
        filename = prescription.prescription_file.name.split('/')[-1]
        response['Content-Disposition'] = f'attachment; filename="{prescription.prescription_number}_{filename}"'
        response['Content-Type'] = 'application/octet-stream'
        return response
        
    except Prescription.DoesNotExist:
        return JsonResponse({'error': 'Prescription not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error downloading file: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def admin_prescription_details(request, prescription_id):
    """Admin endpoint to get prescription details"""
    # Check admin access
    if not (request.session.get("is_admin") or 
            User.objects.filter(user_id=request.session.get("user"), role="admin").exists()):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        prescription = Prescription.objects.select_related(
            'live_appointment',
            'live_appointment__appointment',
            'live_appointment__appointment__patient',
            'live_appointment__appointment__patient__userprofile',
            'live_appointment__appointment__doctor',
            'live_appointment__appointment__doctor__user',
            'live_appointment__appointment__doctor__user__userprofile'
        ).get(prescription_id=prescription_id)
        
        # Extract patient name
        patient = prescription.live_appointment.appointment.patient
        patient_profile = getattr(patient, 'userprofile', None)
        if patient_profile:
            patient_name = f"{patient_profile.first_name or ''} {patient_profile.last_name or ''}".strip()
            if not patient_name:
                patient_name = patient.username
        else:
            patient_name = patient.username
        
        # Extract doctor name
        doctor = prescription.live_appointment.appointment.doctor
        doctor_profile = getattr(doctor.user, 'userprofile', None)
        if doctor_profile:
            doctor_name = f"Dr. {doctor_profile.first_name or ''} {doctor_profile.last_name or ''}".strip()
            if not doctor_name or doctor_name == "Dr. ":
                doctor_name = f"Dr. {doctor.user.username}"
        else:
            doctor_name = f"Dr. {doctor.user.username}"
        
        # Get medicines summary
        medicines_list = prescription.medicines if prescription.medicines else []
        medicines_summary = ', '.join([
            m.get('name', '') for m in medicines_list if isinstance(m, dict) and 'name' in m
        ]) if medicines_list else ''

        return JsonResponse({
            'success': True,
            'prescription': {
                'prescription_id': prescription.prescription_id,
                'prescription_number': prescription.prescription_number,
                'patient_name': patient_name,
                'doctor_name': doctor_name,
                'status': prescription.status,
                'has_file': bool(prescription.prescription_file),
                'medicines_summary': medicines_summary,
                'created_at': prescription.created_at.isoformat() if prescription.created_at else None,
                'instructions': prescription.instructions or '',
                'follow_up_date': prescription.follow_up_date.isoformat() if prescription.follow_up_date else None
            }
        })
        
    except Prescription.DoesNotExist:
        return JsonResponse({'error': 'Prescription not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error fetching details: {str(e)}'}, status=500)


@require_http_methods(["POST"])
def delete_prescription(request, prescription_id):
    """Admin endpoint to delete a prescription"""
    # Check admin access - Super Admin only
    if not request.session.get("is_admin"):
        user_id = request.session.get("user_id") or request.session.get("user")
        if not user_id:
            return JsonResponse({"error": "Unauthorized"}, status=403)
        
        try:
            admin_user = User.objects.get(user_id=user_id, role="admin")
            # Check if super admin
            if not admin_user.is_super_admin:
                return JsonResponse({"error": "Only Super Admin can delete prescriptions"}, status=403)
        except User.DoesNotExist:
            return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        prescription = Prescription.objects.get(prescription_id=prescription_id)
        
        # Delete the prescription file if it exists
        if prescription.prescription_file:
            try:
                prescription.prescription_file.delete()
            except Exception as file_error:
                print(f"Error deleting file: {str(file_error)}")
        
        # Delete the prescription record
        prescription_number = prescription.prescription_number
        prescription.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Prescription {prescription_number} has been deleted successfully'
        })
        
    except Prescription.DoesNotExist:
        return JsonResponse({'error': 'Prescription not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Error deleting prescription: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def admin_lab_result_download(request, result_id):
    """Admin endpoint to download lab result file"""
    # Check admin access
    if not (request.session.get("is_admin") or 
            User.objects.filter(user_id=request.session.get("user"), role="admin").exists()):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        lab_result = LabResult.objects.get(lab_result_id=result_id)
        
        # Decode the base64 file content
        try:
            file_content = base64.b64decode(lab_result.result_file)
        except Exception as e:
            return JsonResponse({"error": f"Error decoding file: {str(e)}"}, status=500)
        
        # Create HTTP response with file
        response = HttpResponse(file_content, content_type=lab_result.file_type or 'application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{lab_result.file_name}"'
        
        return response
        
    except LabResult.DoesNotExist:
        return JsonResponse({"error": "Lab result not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": f"Error downloading file: {str(e)}"}, status=500)

