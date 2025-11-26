from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
import json
from ...models import User, Appointment, Notification
from django.forms.models import model_to_dict

def mod_consultations(request):
    """Appointment management view for admin panel"""
    # Helper function to calculate appointment counts
    def get_appointment_counts():
        """Calculate appointment counts for different time periods"""
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # This week (last 7 days)
        week_start = now - timedelta(days=7)
        
        # This month
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # This year
        year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return {
            'today': Appointment.objects.filter(
                created_at__gte=today_start,
                created_at__lt=today_end
            ).count(),
            'week': Appointment.objects.filter(
                created_at__gte=week_start
            ).count(),
            'month': Appointment.objects.filter(
                created_at__gte=month_start
            ).count(),
            'year': Appointment.objects.filter(
                created_at__gte=year_start
            ).count()
        }
    
    # Check for admin session first
    if request.session.get("is_admin"):
        # Get all appointments with related doctor and patient information
        consultations = Appointment.objects.select_related(
            'doctor', 
            'doctor__user', 
            'doctor__user__userprofile',
            'patient',
            'patient__userprofile'
        ).order_by('-created_at')

        appt_counts = get_appointment_counts()
        context = {
            "consultations": consultations,
            "admin": {"username": "Administrator"},
            "today_appointments_count": appt_counts['today'],
            "week_appointments_count": appt_counts['week'],
            "month_appointments_count": appt_counts['month'],
            "year_appointments_count": appt_counts['year']
        }
        return render(request, "mod_consultations.html", context)

    # Check for regular admin user
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        messages.error(request, "Please login to access admin panel")
        return redirect("homepage2")
    
    try:
        admin_user = User.objects.get(user_id=user_id, role="admin")
        # Get all appointments with related doctor and patient information
        consultations = Appointment.objects.select_related(
            'doctor', 
            'doctor__user', 
            'doctor__user__userprofile',
            'patient',
            'patient__userprofile'
        ).order_by('-created_at')

        appt_counts = get_appointment_counts()
        context = {
            "consultations": consultations,
            "admin": admin_user,
            "today_appointments_count": appt_counts['today'],
            "week_appointments_count": appt_counts['week'],
            "month_appointments_count": appt_counts['month'],
            "year_appointments_count": appt_counts['year']
        }
        return render(request, "mod_consultations.html", context)
    except User.DoesNotExist:
        messages.error(request, "Unauthorized access")
        return redirect("homepage2")

@require_http_methods(["POST"])
def update_consultation_status(request):
    """Update the status of an appointment (approve/reject/complete)"""
    if not (request.session.get("is_admin") or 
            User.objects.filter(user_id=request.session.get("user"), role="admin").exists()):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        data = json.loads(request.body)
        consultation_id = data.get('consultation_id')
        status = data.get('status')
        is_completion = data.get('is_completion', False)

        if not all([consultation_id, status]):
            return JsonResponse({
                "error": "Appointment ID and status are required"
            }, status=400)

        consultation = Appointment.objects.get(consultation_id=consultation_id)

        if is_completion:
            consultation.status = status
        else:
            consultation.approval_status = status
            # If rejected, also update the status
            if status == 'Rejected':
                consultation.status = 'Cancelled'

        consultation.updated_at = timezone.now()
        consultation.save()

        # Create patient-facing notifications based on status change
        try:
            patient_user = consultation.patient
            if is_completion and status == 'Completed':
                Notification.objects.create(
                    user=patient_user,
                    title="Appointment Completed",
                    message=f"Your appointment with Dr. {consultation.doctor.user.get_full_name()} on {consultation.consultation_date} has been marked completed.",
                    notification_type='appointment',
                    priority='low',
                    related_id=consultation.consultation_id
                )
            elif not is_completion:
                if status == 'Approved':
                    Notification.objects.create(
                        user=patient_user,
                        title="Appointment Approved",
                        message=f"Your appointment on {consultation.consultation_date} at {consultation.consultation_time} has been approved.",
                        notification_type='appointment',
                        priority='medium',
                        related_id=consultation.consultation_id
                    )
                elif status == 'Rejected':
                    Notification.objects.create(
                        user=patient_user,
                        title="Appointment Rejected",
                        message=f"Your appointment on {consultation.consultation_date} was rejected and set to Cancelled.",
                        notification_type='urgent',
                        priority='high',
                        related_id=consultation.consultation_id
                    )
                elif status == 'Pending':
                    Notification.objects.create(
                        user=patient_user,
                        title="Appointment Pending",
                        message=f"Your appointment on {consultation.consultation_date} is pending review.",
                        notification_type='appointment',
                        priority='low',
                        related_id=consultation.consultation_id
                    )
        except Exception:
            # Don't break admin flow if notifications fail
            pass

        return JsonResponse({
            "success": True,
            "message": f"Appointment {status.lower()} successfully"
        })

    except Appointment.DoesNotExist:
        return JsonResponse({"error": "Appointment not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@require_http_methods(["GET"])
def get_consultation_details(request):
    """Return appointment details for editing/approval modal"""
    if not (request.session.get("is_admin") or 
            User.objects.filter(user_id=request.session.get("user"), role="admin").exists()):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    consultation_id = request.GET.get('consultation_id')
    if not consultation_id:
        return JsonResponse({"error": "Appointment ID is required"}, status=400)

    try:
        appt = Appointment.objects.select_related(
            'doctor', 'doctor__user', 'doctor__user__userprofile',
            'patient', 'patient__userprofile'
        ).get(consultation_id=consultation_id)

        data = model_to_dict(appt, fields=[
            'consultation_id', 'consultation_type', 'consultation_date', 'consultation_time',
            'approval_status', 'status', 'notes', 'meeting_link', 'appointment_number'
        ])
        data.update({
            'patient_name': appt.patient.get_full_name(),
            'doctor_name': appt.doctor.user.get_full_name(),
        })
        return JsonResponse({"success": True, "appointment": data})
    except Appointment.DoesNotExist:
        return JsonResponse({"error": "Appointment not found"}, status=404)

@csrf_exempt
@require_http_methods(["POST"])
def save_consultation(request):
    """Save appointment edits and optionally approve"""
    if not (request.session.get("is_admin") or 
            User.objects.filter(user_id=request.session.get("user"), role="admin").exists()):
        return JsonResponse({"error": "Unauthorized"}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    consultation_id = data.get('consultation_id')
    if not consultation_id:
        return JsonResponse({"error": "Appointment ID is required"}, status=400)

    try:
        appt = Appointment.objects.get(consultation_id=consultation_id)

        # Update editable fields
        if data.get('consultation_type') in ['F2F', 'Tele']:
            appt.consultation_type = data['consultation_type']
        if data.get('consultation_date'):
            appt.consultation_date = data['consultation_date']
        if data.get('consultation_time'):
            appt.consultation_time = data['consultation_time']
        if 'notes' in data:
            appt.notes = data.get('notes')
        if 'appointment_number' in data:
            appt.appointment_number = (data.get('appointment_number') or '').strip() or None
        if appt.consultation_type == 'Tele':
            # Require meeting_link for teleconsult
            if not data.get('meeting_link'):
                return JsonResponse({"error": "Meeting link is required for tele-consultation"}, status=400)
            appt.meeting_link = data.get('meeting_link')
        else:
            # Clear link for F2F
            appt.meeting_link = None

        # Approve if requested
        if data.get('approve'):
            # Require appointment number when approving
            provided_appt_no = (data.get('appointment_number') or '').strip()
            existing_appt_no = appt.appointment_number or ''
            if not (provided_appt_no or existing_appt_no):
                return JsonResponse({"error": "Appointment number is required to approve an appointment."}, status=400)

            appt.approval_status = 'Approved'
            appt.approved_at = timezone.now()
        
        # Reject if requested
        if data.get('reject'):
            appt.approval_status = 'Rejected'
            appt.status = 'Cancelled'
            appt.approved_at = timezone.now()

        appt.updated_at = timezone.now()
        appt.save()

        # Return appropriate message
        if data.get('approve'):
            message = "Appointment approved successfully"
        elif data.get('reject'):
            message = "Appointment rejected successfully"
        else:
            message = "Appointment saved successfully"

        # Create notifications for the patient user
        try:
            patient_user = appt.patient
            if data.get('approve'):
                Notification.objects.create(
                    user=patient_user,
                    title="Appointment Approved",
                    message=f"Your appointment on {appt.consultation_date} at {appt.consultation_time} has been approved.",
                    notification_type='appointment',
                    priority='medium',
                    related_id=appt.consultation_id
                )
            elif data.get('reject'):
                Notification.objects.create(
                    user=patient_user,
                    title="Appointment Rejected",
                    message=f"Your appointment on {appt.consultation_date} was rejected and set to Cancelled.",
                    notification_type='urgent',
                    priority='high',
                    related_id=appt.consultation_id
                )
            else:
                Notification.objects.create(
                    user=patient_user,
                    title="Appointment Updated",
                    message=f"Your appointment details for {appt.consultation_date} may have changed.",
                    notification_type='appointment',
                    priority='low',
                    related_id=appt.consultation_id
                )
        except Exception:
            pass

        return JsonResponse({"success": True, "message": message})
    except Appointment.DoesNotExist:
        return JsonResponse({"error": "Appointment not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def delete_consultation(request):
    """Delete an appointment"""
    if not (request.session.get("is_admin") or 
            User.objects.filter(user_id=request.session.get("user"), role="admin").exists()):
        return JsonResponse({"error": "Admin access required"}, status=403)

    try:
        if not request.body:
            return JsonResponse({"error": "Request body is empty"}, status=400)

        data = json.loads(request.body)
        consultation_id = data.get('consultation_id')
        
        if not consultation_id:
            return JsonResponse({"error": "Appointment ID is required"}, status=400)

        try:
            consultation = Appointment.objects.get(consultation_id=consultation_id)
            consultation.delete()
            return JsonResponse({
                "success": True,
                "message": "Appointment deleted successfully",
                "consultation_id": consultation_id
            })
        except Appointment.DoesNotExist:
            return JsonResponse({"error": "Appointment not found"}, status=404)
            
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        print(f"Error in delete_consultation: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)
