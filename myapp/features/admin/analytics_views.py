from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Count, Q, Avg, Max, Min, StdDev, Variance
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
import json
import csv
import statistics
from ...models import User, UserProfile, Patient, Doctor, Appointment, BookedService, LabResult

def analytics(request):
    """Analytics dashboard with comprehensive statistics and charts"""
    if request.session.get("is_admin"):
        admin_user = {"username": "Administrator"}
    else:
        user_id = request.session.get("user_id") or request.session.get("user")
        if not user_id:
            messages.error(request, "Please login to view analytics")
            return redirect("homepage2")
        
        try:
            admin_user = User.objects.get(user_id=user_id, role="admin")
        except User.DoesNotExist:
            messages.error(request, "Unauthorized access")
            return redirect("homepage2")

    # Get comprehensive analytics data
    try:
        # Timeframe handling - support Day, Week, Month
        timeframe_param = request.GET.get('timeframe', 'month')
        timeframe_type = request.GET.get('timeframe_type', 'days')  # days, week, month
        
        now = datetime.now()
        if timeframe_param == 'day' or timeframe_type == 'day':
            timeframe_days = 1
            timeframe_start = now - timedelta(days=1)
        elif timeframe_param == 'week' or timeframe_type == 'week':
            timeframe_days = 7
            timeframe_start = now - timedelta(days=7)
        elif timeframe_param == 'month' or timeframe_type == 'month':
            timeframe_days = 30
            timeframe_start = now - timedelta(days=30)
        else:
            # Fallback to numeric days (for backward compatibility)
            try:
                timeframe_days = int(timeframe_param)
                if timeframe_days not in [1, 7, 30, 90]:
                    timeframe_days = 30
            except ValueError:
                timeframe_days = 30
            timeframe_start = now - timedelta(days=timeframe_days)
        
        # Sort parameter for doctor performance
        doctor_sort = request.GET.get('doctor_sort', 'consultations')  # consultations or specialization

        # Basic statistics
        total_users = User.objects.count()
        total_patients = Patient.objects.count()
        total_doctors = Doctor.objects.count()
        total_consultations = Appointment.objects.count()
        total_completed_consultations = Appointment.objects.filter(status='Completed').count()
        
        # User role distribution - Include all roles, even if count is 0
        all_roles = ['admin', 'doctor', 'nurse', 'lab_tech', 'patient']
        user_roles = User.objects.values('role').annotate(count=Count('role'))
        role_counts = {item['role']: item['count'] for item in user_roles}
        # Ensure all roles are included with proper counts
        role_distribution = {}
        for role in all_roles:
            role_distribution[role] = role_counts.get(role, 0)
        
        # Active vs Inactive users
        active_users = User.objects.filter(is_active=True).count()
        inactive_users = User.objects.filter(is_active=False).count()
        
        # Recent activity (last N days by timeframe)
        recent_users = User.objects.filter(date_joined__gte=timeframe_start).count()
        recent_consultations = Appointment.objects.filter(created_at__gte=timeframe_start).count()
        completed_consultations_timeframe = Appointment.objects.filter(status='Completed', created_at__gte=timeframe_start).count()
        
        # Consultation statistics
        consultation_status = Appointment.objects.values('status').annotate(count=Count('status'))
        consultation_types = Appointment.objects.values('consultation_type').annotate(count=Count('consultation_type'))
        
        # Convert QuerySets to lists for JSON serialization (must be done before using in statistics)
        consultation_status_list = list(consultation_status)
        consultation_types_list = list(consultation_types)
        
        # Monthly consultation trends (last 6 months)
        monthly_consultations = []
        for i in range(6):
            month_start = now - timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            count = Appointment.objects.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            ).count()
            monthly_consultations.append({
                'month': month_start.strftime('%Y-%m'),
                'count': count
            })
        
        # Doctor performance (consultations per doctor)
        doctor_performance_qs = Doctor.objects.select_related('user').annotate(
            consultation_count=Count('doctor_consultations', filter=Q(doctor_consultations__created_at__gte=timeframe_start))
        )
        
        # Sort by specialization or consultations
        if doctor_sort == 'specialization':
            # Group by specialization and aggregate consultation counts
            from django.db.models import Sum
            specialization_performance = Doctor.objects.values('specialization').annotate(
                total_consultations=Count('doctor_consultations', filter=Q(doctor_consultations__created_at__gte=timeframe_start))
            ).order_by('-total_consultations')[:10]
            doctor_performance_qs = None  # Will use specialization_performance instead
        else:
            doctor_performance_qs = doctor_performance_qs.order_by('-consultation_count')[:10]
        
        # Top Performing Fields (Specializations) - Always calculate for the fields tab
        fields_performance = Doctor.objects.values('specialization').annotate(
            total_consultations=Count('doctor_consultations', filter=Q(doctor_consultations__created_at__gte=timeframe_start))
        ).order_by('-total_consultations')[:15]
        
        # Calculate fields statistics
        fields_counts = [item['total_consultations'] or 0 for item in fields_performance]
        fields_stats = {}
        if fields_counts and len(fields_counts) > 0:
            try:
                fields_stats = {
                    'mean': round(statistics.mean(fields_counts), 2),
                    'median': round(statistics.median(fields_counts), 2),
                    'std_dev': round(statistics.stdev(fields_counts), 2) if len(fields_counts) > 1 else 0,
                    'min': min(fields_counts),
                    'max': max(fields_counts),
                    'range': max(fields_counts) - min(fields_counts),
                    'total_specializations': len(fields_counts),
                    'top_specialization': fields_performance[0]['specialization'] if fields_performance else None,
                }
            except Exception:
                fields_stats = {}
        

        
        # Booked Services statistics
        booked_services_total = BookedService.objects.count()
        booked_services_timeframe = BookedService.objects.filter(booking_date__gte=timeframe_start.date()).count()
        booked_services_by_status = BookedService.objects.values('status').annotate(count=Count('status'))
        booked_services_status_distribution = {item['status']: item['count'] for item in booked_services_by_status}
        booked_services_by_service = BookedService.objects.values('service_name').annotate(count=Count('service_name'))
        booked_services_service_distribution = {item['service_name']: item['count'] for item in booked_services_by_service}
        
        # Recent registrations (within timeframe)
        recent_registrations = User.objects.filter(date_joined__gte=timeframe_start).count()
        
        # Lab Results statistics
        total_lab_results = LabResult.objects.count()
        lab_results_timeframe = LabResult.objects.filter(upload_date__gte=timeframe_start).count()
        
        # Lab Results by month (for monthly trends replacement)
        lab_results_by_month = []
        for i in range(6):
            month_start = now - timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            count = LabResult.objects.filter(
                upload_date__gte=month_start,
                upload_date__lt=month_end
            ).count()
            lab_results_by_month.append({
                'month': month_start.strftime('%Y-%m'),
                'count': count
            })
        
        # Lab Results by type
        lab_results_by_type = LabResult.objects.values('lab_type').annotate(count=Count('lab_type'))
        lab_results_type_distribution = {item['lab_type']: item['count'] for item in lab_results_by_type}
        
        # Consultation approval rates
        total_pending = Appointment.objects.filter(approval_status='Pending').count()
        total_approved = Appointment.objects.filter(approval_status='Approved').count()
        total_rejected = Appointment.objects.filter(approval_status='Rejected').count()
        
        approval_rate = (total_approved / (total_approved + total_rejected)) * 100 if (total_approved + total_rejected) > 0 else 0
        
        # ===== HELPER FUNCTION FOR ADAPTIVE CAPTIONS (DEFINED EARLY TO AVOID SCOPE ISSUES) =====
        def generate_caption(stats, data_type, role_dist=None):
            """Generate adaptive, descriptive captions based on statistical data"""
            if not stats:
                return "Insufficient data for statistical analysis."
            
            captions = []
            
            # For roles - describe the distribution
            if data_type == 'User Roles' and role_dist:
                role_names = {
                    'admin': 'Administrators',
                    'doctor': 'Doctors',
                    'nurse': 'Nurses',
                    'lab_tech': 'Lab Technicians',
                    'patient': 'Patients'
                }
                total_users = sum(role_dist.values())
                if total_users > 0:
                    role_parts = []
                    for role in ['admin', 'doctor', 'nurse', 'lab_tech', 'patient']:
                        count = role_dist.get(role, 0)
                        if count > 0:
                            pct = (count / total_users) * 100
                            role_parts.append(f"{role_names.get(role, role)}: {count} ({pct:.1f}%)")
                    if role_parts:
                        captions.append(f"User composition - {', '.join(role_parts)}. Total: {total_users} users.")
                return " ".join(captions) if captions else ""
            
            # Central tendency and summary statistics
            if stats.get('mean') is not None:
                mean_val = stats['mean']
                max_val = stats.get('max', 0)
                min_val = stats.get('min', 0)
                captions.append(f"Average: {mean_val:.1f}, ranging from {min_val} to {max_val}.")
            
            # Consistency analysis (without high variability warning)
            if stats.get('std_dev', 0) > 0 and stats.get('mean', 0) > 0:
                cv = (stats['std_dev'] / stats['mean']) * 100
                if cv < 25:
                    captions.append(f"Consistent distribution (CV: {cv:.1f}%) indicates stable {data_type.lower()} patterns.")
                else:
                    captions.append(f"Distribution shows variation (CV: {cv:.1f}%) across {data_type.lower()} categories.")
            
            # Most common element
            if stats.get('most_common'):
                captions.append(f"Most common: {stats['most_common']} with {stats.get('max', 0)} entries.")
            
            # Total information
            if stats.get('total_roles'):
                captions.append(f"{stats['total_roles']} distinct roles identified.")
            if stats.get('total_statuses'):
                captions.append(f"{stats['total_statuses']} different appointment statuses tracked.")
            if stats.get('total_types'):
                captions.append(f"{stats['total_types']} different lab result types recorded.")
            if stats.get('total_doctors'):
                captions.append(f"{stats['total_doctors']} doctors contributing to statistics.")
            
            return " ".join(captions) if captions else f"Analysis of {data_type.lower()}"
        
        # ===== DESCRIPTIVE STATISTICS =====
        # Calculate statistics for monthly consultations
        monthly_counts = [item['count'] for item in monthly_consultations]
        monthly_stats = {}
        if monthly_counts and len(monthly_counts) > 0:
            try:
                monthly_stats = {
                    'mean': round(statistics.mean(monthly_counts), 2),
                    'median': round(statistics.median(monthly_counts), 2),
                    'std_dev': round(statistics.stdev(monthly_counts), 2) if len(monthly_counts) > 1 else 0,
                    'min': min(monthly_counts),
                    'max': max(monthly_counts),
                    'range': max(monthly_counts) - min(monthly_counts),
                    'variance': round(statistics.variance(monthly_counts), 2) if len(monthly_counts) > 1 else 0,
                }
            except Exception:
                monthly_stats = {}
        
        # Calculate statistics for doctor performance
        if doctor_sort == 'specialization' and 'specialization_performance' in locals():
            # Use specialization data
            specialization_counts = [item['total_consultations'] or 0 for item in specialization_performance]
            doctor_stats = {}
            if specialization_counts and len(specialization_counts) > 0:
                try:
                    doctor_stats = {
                        'mean': round(statistics.mean(specialization_counts), 2),
                        'median': round(statistics.median(specialization_counts), 2),
                        'std_dev': round(statistics.stdev(specialization_counts), 2) if len(specialization_counts) > 1 else 0,
                        'min': min(specialization_counts),
                        'max': max(specialization_counts),
                        'range': max(specialization_counts) - min(specialization_counts),
                        'total_doctors': len(specialization_counts),
                    }
                except Exception:
                    doctor_stats = {}
        else:
            doctor_counts = [d.consultation_count for d in doctor_performance_qs] if doctor_performance_qs else []
            doctor_stats = {}
            if doctor_counts and len(doctor_counts) > 0:
                try:
                    doctor_stats = {
                        'mean': round(statistics.mean(doctor_counts), 2),
                        'median': round(statistics.median(doctor_counts), 2),
                        'std_dev': round(statistics.stdev(doctor_counts), 2) if len(doctor_counts) > 1 else 0,
                        'min': min(doctor_counts),
                        'max': max(doctor_counts),
                        'range': max(doctor_counts) - min(doctor_counts),
                        'total_doctors': len(doctor_counts),
                    }
                except Exception:
                    doctor_stats = {}
        
        # Booked Services statistics
        booked_services_counts = list(booked_services_status_distribution.values())
        booked_services_stats = {}
        if booked_services_counts and len(booked_services_counts) > 0:
            try:
                booked_services_stats = {
                    'mean': round(statistics.mean(booked_services_counts), 2),
                    'median': round(statistics.median(booked_services_counts), 2),
                    'std_dev': round(statistics.stdev(booked_services_counts), 2) if len(booked_services_counts) > 1 else 0,
                    'min': min(booked_services_counts),
                    'max': max(booked_services_counts),
                    'total_statuses': len(booked_services_counts),
                    'most_common': max(booked_services_status_distribution.items(), key=lambda x: x[1])[0] if booked_services_status_distribution else None,
                }
            except Exception:
                booked_services_stats = {}
        
        # Role distribution statistics
        role_counts = list(role_distribution.values())
        role_stats = {}
        if role_counts and len(role_counts) > 0:
            try:
                role_stats = {
                    'mean': round(statistics.mean(role_counts), 2),
                    'median': round(statistics.median(role_counts), 2),
                    'std_dev': round(statistics.stdev(role_counts), 2) if len(role_counts) > 1 else 0,
                    'min': min(role_counts),
                    'max': max(role_counts),
                    'total_roles': len(role_counts),
                    'most_common': max(role_distribution.items(), key=lambda x: x[1])[0] if role_distribution else None,
                }
            except Exception:
                role_stats = {}
        

        
        # Consultation status statistics
        status_counts = [item['count'] for item in consultation_status_list]
        status_stats = {}
        if status_counts and len(status_counts) > 0:
            try:
                status_stats = {
                    'mean': round(statistics.mean(status_counts), 2),
                    'median': round(statistics.median(status_counts), 2),
                    'std_dev': round(statistics.stdev(status_counts), 2) if len(status_counts) > 1 else 0,
                    'min': min(status_counts),
                    'max': max(status_counts),
                    'total_statuses': len(status_counts),
                }
            except Exception:
                status_stats = {}
        
        # Lab Results statistics
        lab_results_stats = {}
        lab_results_monthly_counts = [item['count'] for item in lab_results_by_month]
        if lab_results_monthly_counts and len(lab_results_monthly_counts) > 0:
            try:
                lab_results_stats = {
                    'mean': round(statistics.mean(lab_results_monthly_counts), 2),
                    'median': round(statistics.median(lab_results_monthly_counts), 2),
                    'std_dev': round(statistics.stdev(lab_results_monthly_counts), 2) if len(lab_results_monthly_counts) > 1 else 0,
                    'min': min(lab_results_monthly_counts),
                    'max': max(lab_results_monthly_counts),
                    'total_types': len(lab_results_type_distribution),
                }
            except Exception:
                lab_results_stats = {}
        
        # Generate adaptive captions (function already defined above)
        monthly_caption = generate_caption(monthly_stats, "Monthly Consultations")
        doctor_caption = generate_caption(doctor_stats, "Doctor Performance")
        role_caption = generate_caption(role_stats, "User Roles", role_distribution)
        status_caption = generate_caption(status_stats, "Appointment Status")
        booked_services_caption = generate_caption(booked_services_stats, "Booked Services")
        lab_results_caption = generate_caption(lab_results_stats, "Lab Results")
        fields_caption = generate_caption(fields_stats, "Specialization Performance")
        
        # Doctor performance list for JSON serialization
        if doctor_sort == 'specialization' and 'specialization_performance' in locals():
            doctor_performance_list = [
                {
                    'name': item['specialization'] or 'Unknown',
                    'username': item['specialization'] or 'Unknown',
                    'consultation_count': item['total_consultations'] or 0,
                    'specialization': item['specialization'] or 'Unknown',
                }
                for item in specialization_performance
            ]
        else:
            doctor_performance_list = [
                {
                    'name': (d.user.get_full_name() if hasattr(d.user, 'get_full_name') else d.user.username),
                    'username': d.user.username,
                    'consultation_count': d.consultation_count,
                    'specialization': d.specialization,
                }
                for d in doctor_performance_qs
            ]
        
        # Fields performance list for JSON serialization
        fields_performance_list = [
            {
                'specialization': item['specialization'] or 'Unknown',
                'consultation_count': item['total_consultations'] or 0,
            }
            for item in fields_performance
        ]
        
        # Create fields distribution dictionary
        fields_distribution = {item['specialization'] or 'Unknown': item['total_consultations'] or 0 for item in fields_performance}
        
        context = {
            'admin': admin_user,
            'total_users': total_users,
            'total_patients': total_patients,
            'total_doctors': total_doctors,
            'total_consultations': total_consultations,
            'total_completed_consultations': total_completed_consultations,
            'active_users': active_users,
            'inactive_users': inactive_users,
            'recent_users': recent_users,
            'recent_consultations': recent_consultations,
            'completed_consultations_timeframe': completed_consultations_timeframe,
            'role_distribution': json.dumps(role_distribution),
            'consultation_status': json.dumps(consultation_status_list),
            'consultation_types': json.dumps(consultation_types_list),
            'monthly_consultations': json.dumps(monthly_consultations),
            'doctor_performance': json.dumps(doctor_performance_list),
            'recent_registrations': recent_registrations,
            'approval_rate': round(approval_rate, 2),
            'total_pending': total_pending,
            'total_approved': total_approved,
            'total_rejected': total_rejected,
            'timeframe_days': timeframe_days,
            'timeframe_type': timeframe_param if timeframe_param in ['day', 'week', 'month'] else 'month',
            'doctor_sort': doctor_sort,
            # Descriptive statistics
            'monthly_stats': monthly_stats,
            'doctor_stats': doctor_stats,
            'role_stats': role_stats,
            'status_stats': status_stats,
            'booked_services_stats': booked_services_stats,
            # Adaptive captions
            'monthly_caption': monthly_caption,
            'doctor_caption': doctor_caption,
            'role_caption': role_caption,
            'status_caption': status_caption,
            'booked_services_caption': booked_services_caption,
            'lab_results_caption': lab_results_caption,
            # Booked Services data
            'booked_services_total': booked_services_total,
            'booked_services_timeframe': booked_services_timeframe,
            'booked_services_status_distribution': json.dumps(booked_services_status_distribution),
            'booked_services_service_distribution': json.dumps(booked_services_service_distribution),
            # Lab Results data
            'total_lab_results': total_lab_results,
            'lab_results_timeframe': lab_results_timeframe,
            'lab_results_by_month': json.dumps(lab_results_by_month),
            'lab_results_type_distribution': json.dumps(lab_results_type_distribution),
            'lab_results_stats': lab_results_stats,
            # Fields performance data
            'fields_performance': json.dumps(fields_performance_list),
            'fields_distribution': json.dumps(fields_distribution),
            'fields_stats': fields_stats,
            'fields_caption': fields_caption,
        }

        # Optional CSV export
        if request.GET.get('export') == 'csv':
            response = HttpResponse(content_type='text/csv')
            filename = f"analytics_kpis_{now.strftime('%Y%m%d')}.csv"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            writer = csv.writer(response)
            writer.writerow(['KPI', 'Value', 'TimeframeDays'])
            writer.writerow(['Total Users', total_users, timeframe_days])
            writer.writerow(['Total Patients', total_patients, timeframe_days])
            writer.writerow(['Total Doctors', total_doctors, timeframe_days])
            writer.writerow(['Total Consultations', total_consultations, timeframe_days])
            writer.writerow(['Total Completed Consultations', total_completed_consultations, timeframe_days])
            writer.writerow(['Active Users', active_users, timeframe_days])
            writer.writerow(['Inactive Users', inactive_users, timeframe_days])
            writer.writerow(['Recent Users', recent_users, timeframe_days])
            writer.writerow(['Recent Consultations', recent_consultations, timeframe_days])
            writer.writerow(['Completed Consultations (Timeframe)', completed_consultations_timeframe, timeframe_days])
            writer.writerow(['Approval Rate (%)', round(approval_rate, 2), timeframe_days])
            writer.writerow(['Pending Consultations', total_pending, timeframe_days])
            writer.writerow(['Approved Consultations', total_approved, timeframe_days])
            writer.writerow(['Rejected Consultations', total_rejected, timeframe_days])
            return response

        # Doctor performance CSV export
        if request.GET.get('export') == 'doctor_csv':
            response = HttpResponse(content_type='text/csv')
            filename = f"doctor_performance_{now.strftime('%Y%m%d')}.csv"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            writer = csv.writer(response)
            writer.writerow(['Doctor', 'Username', 'Consultations', 'TimeframeDays'])
            for item in doctor_performance_list:
                writer.writerow([item.get('name') or item.get('username'), item.get('username'), item.get('consultation_count'), timeframe_days])
            return response

        return render(request, "mod_analytics.html", context)
        
    except Exception as e:
        messages.error(request, f"Error loading analytics: {str(e)}")
        return redirect("homepage2")

@require_http_methods(["GET"])
def analytics_api(request):
    """API endpoint for live analytics updates"""
    if not (request.session.get("is_admin") or 
            User.objects.filter(user_id=request.session.get("user"), role="admin").exists()):
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        # Get timeframe and doctor_sort from query params
        timeframe_param = request.GET.get('timeframe', 'month')
        doctor_sort = request.GET.get('doctor_sort', 'consultations')
        
        # Calculate timeframe
        now = datetime.now()
        if timeframe_param == 'day':
            timeframe_days = 1
            timeframe_start = now - timedelta(days=1)
        elif timeframe_param == 'week':
            timeframe_days = 7
            timeframe_start = now - timedelta(days=7)
        elif timeframe_param == 'month':
            timeframe_days = 30
            timeframe_start = now - timedelta(days=30)
        else:
            timeframe_days = 30
            timeframe_start = now - timedelta(days=30)
        
        # Get all the same data as the main analytics view
        # (This is a simplified version - you may want to refactor to share code)
        total_users = User.objects.count()
        total_patients = Patient.objects.count()
        total_doctors = Doctor.objects.count()
        total_consultations = Appointment.objects.count()
        
        # Role distribution - Include all roles, even if count is 0
        all_roles = ['admin', 'doctor', 'nurse', 'lab_tech', 'patient']
        role_distribution = {}
        for role in all_roles:
            count = User.objects.filter(role=role).count()
            role_distribution[role] = count
        
        # Consultation status
        consultation_status_list = list(
            Appointment.objects.values('status')
            .annotate(count=Count('status'))
            .order_by('-count')
        )
        
        # Monthly consultations
        monthly_consultations = list(
            Appointment.objects.filter(created_at__gte=timeframe_start)
            .extra(select={'month': "DATE_FORMAT(created_at, '%%Y-%%m')"})
            .values('month')
            .annotate(count=Count('consultation_id'))
            .order_by('month')
        )
        
        # Doctor performance
        doctor_performance_qs = Doctor.objects.select_related('user').annotate(
            consultation_count=Count('doctor_consultations', filter=Q(doctor_consultations__created_at__gte=timeframe_start))
        )
        
        if doctor_sort == 'specialization':
            specialization_performance = Doctor.objects.values('specialization').annotate(
                total_consultations=Count('doctor_consultations', filter=Q(doctor_consultations__created_at__gte=timeframe_start))
            ).order_by('-total_consultations')[:10]
            doctor_performance_list = [
                {
                    'specialization': item['specialization'] or 'Unknown',
                    'consultation_count': item['total_consultations']
                }
                for item in specialization_performance
            ]
        else:
            doctor_performance_qs = doctor_performance_qs.order_by('-consultation_count')[:10]
            doctor_performance_list = [
                {
                    'name': d.user.get_full_name() if d.user else d.user.username,
                    'username': d.user.username if d.user else 'Unknown',
                    'specialization': d.specialization or 'Unknown',
                    'consultation_count': d.consultation_count
                }
                for d in doctor_performance_qs
            ]
        
        # Gender distribution
        gender_distribution = {}
        for gender in ['male', 'female', 'other']:
            count = UserProfile.objects.filter(sex=gender).count()
            if count > 0:
                gender_distribution[gender] = count
        
        # Blood type distribution
        blood_type_distribution = {}
        for blood_type in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
            count = Patient.objects.filter(blood_type=blood_type).count()
            if count > 0:
                blood_type_distribution[blood_type] = count
        
        # Booked services
        booked_services_status_distribution = {}
        for status in ['Pending', 'Confirmed', 'Completed', 'Cancelled']:
            count = BookedService.objects.filter(status=status).count()
            if count > 0:
                booked_services_status_distribution[status] = count
        
        booked_services_service_distribution = {}
        for service in BookedService.objects.values_list('service_name', flat=True).distinct():
            count = BookedService.objects.filter(service_name=service).count()
            if count > 0:
                booked_services_service_distribution[service] = count
        
        # Fields distribution for API
        fields_performance_api = Doctor.objects.values('specialization').annotate(
            total_consultations=Count('doctor_consultations', filter=Q(doctor_consultations__created_at__gte=timeframe_start))
        ).order_by('-total_consultations')[:15]
        fields_distribution_api = {item['specialization'] or 'Unknown': item['total_consultations'] or 0 for item in fields_performance_api}
        
        # Lab Results for API
        lab_results_by_month_api = []
        for i in range(6):
            month_start = now - timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            count = LabResult.objects.filter(
                upload_date__gte=month_start,
                upload_date__lt=month_end
            ).count()
            lab_results_by_month_api.append({
                'month': month_start.strftime('%Y-%m'),
                'count': count
            })
        
        total_lab_results_api = LabResult.objects.count()
        total_booked_services_api = BookedService.objects.count()
        
        return JsonResponse({
            'role_distribution': role_distribution,
            'consultation_status': consultation_status_list,
            'monthly_consultations': monthly_consultations,
            'lab_results_by_month': lab_results_by_month_api,
            'doctor_performance': doctor_performance_list,
            'gender_distribution': gender_distribution,
            'blood_type_distribution': blood_type_distribution,
            'booked_services_status_distribution': booked_services_status_distribution,
            'booked_services_service_distribution': booked_services_service_distribution,
            'fields_distribution': fields_distribution_api,
            'total_lab_results': total_lab_results_api,
            'total_booked_services': total_booked_services_api,
            'doctor_sort': doctor_sort,
            'timeframe': timeframe_param
        })
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_http_methods(["GET"])
def get_dynamic_statistics(request):
    """Get statistics for a specific time period (daily, weekly, monthly)"""
    try:
        # Check authorization
        if request.session.get("is_admin"):
            admin_user = True
        else:
            user_id = request.session.get("user_id") or request.session.get("user")
            if not user_id:
                return JsonResponse({"error": "Unauthorized"}, status=403)
            try:
                User.objects.get(user_id=user_id, role="admin")
                admin_user = True
            except User.DoesNotExist:
                return JsonResponse({"error": "Unauthorized"}, status=403)
        
        period_type = request.GET.get('period_type', 'monthly')  # daily, weekly, monthly
        year = int(request.GET.get('year', datetime.now().year))
        month = int(request.GET.get('month', datetime.now().month))
        week = int(request.GET.get('week', 1))
        day = int(request.GET.get('day', datetime.now().day))
        
        now = datetime.now()
        
        if period_type == 'daily':
            # Daily statistics for a specific date
            target_date = datetime(year, month, day)
            period_start = target_date
            period_end = target_date + timedelta(days=1)
            period_label = target_date.strftime('%Y-%m-%d')
        
        elif period_type == 'weekly':
            # Weekly statistics for a specific week in a month
            # Calculate week start date
            first_day = datetime(year, month, 1)
            # Get the week containing the first day of the month
            days_in_month = 31 if month in [1,3,5,7,8,10,12] else (30 if month in [4,6,9,11] else (29 if year % 4 == 0 else 28))
            
            # Calculate week boundaries
            week_num = max(1, week)
            period_start = first_day + timedelta(weeks=week_num-1)
            period_end = period_start + timedelta(weeks=1)
            
            # Ensure we stay within the month
            if period_start.month != month:
                period_start = first_day
            if period_end.month != month:
                period_end = datetime(year, month, days_in_month) + timedelta(days=1)
            
            period_label = f"{year}-{month:02d} Week {week_num}"
        
        else:  # monthly
            # Monthly statistics for a specific month
            period_start = datetime(year, month, 1)
            if month == 12:
                period_end = datetime(year + 1, 1, 1)
            else:
                period_end = datetime(year, month + 1, 1)
            period_label = f"{year}-{month:02d}"
        
        # Calculate statistics for the period - Include all roles
        all_roles = ['admin', 'doctor', 'nurse', 'lab_tech', 'patient']
        role_distribution = {}
        user_roles = User.objects.filter(date_joined__gte=period_start, date_joined__lt=period_end).values('role').annotate(count=Count('role'))
        role_counts = {item['role']: item['count'] for item in user_roles}
        # Include all roles, even if 0 count for selected period
        for role in all_roles:
            role_distribution[role] = role_counts.get(role, 0)
        
        # Consultation status distribution
        consultation_status_list = []
        consultation_status = Appointment.objects.filter(created_at__gte=period_start, created_at__lt=period_end).values('status').annotate(count=Count('status'))
        consultation_status_list = list(consultation_status)
        
        # Monthly trends (if period type is not monthly, still show monthly data)
        if period_type != 'monthly':
            monthly_data = []
            for i in range(6):
                month_date = period_start - timedelta(days=30*i)
                month_data_start = month_date.replace(day=1)
                if month_date.month == 12:
                    month_data_end = (month_date.replace(year=month_date.year+1, month=1))
                else:
                    month_data_end = month_date.replace(month=month_date.month+1)
                count = Appointment.objects.filter(created_at__gte=month_data_start, created_at__lt=month_data_end).count()
                monthly_data.append({'month': month_date.strftime('%Y-%m'), 'count': count})
            monthly_consultations = monthly_data
        else:
            # For monthly period type, show data for the selected month only
            monthly_consultations = [{
                'month': period_label,
                'count': Appointment.objects.filter(created_at__gte=period_start, created_at__lt=period_end).count()
            }]
        
        # Doctor performance
        doctor_performance_qs = Doctor.objects.select_related('user').annotate(
            consultation_count=Count('doctor_consultations', filter=Q(doctor_consultations__created_at__gte=period_start, doctor_consultations__created_at__lt=period_end))
        ).order_by('-consultation_count')[:10]
        
        doctor_performance_list = [
            {
                'name': d.user.get_full_name() if d.user else d.user.username,
                'username': d.user.username if d.user else 'Unknown',
                'specialization': d.specialization or 'Unknown',
                'consultation_count': d.consultation_count
            }
            for d in doctor_performance_qs
        ]
        
        # Statistics calculations
        def calculate_stats(data_list):
            if not data_list or len(data_list) == 0:
                return {}
            try:
                values = [v for v in data_list if isinstance(v, (int, float))]
                if not values:
                    return {}
                return {
                    'mean': round(statistics.mean(values), 2),
                    'median': round(statistics.median(values), 2),
                    'std_dev': round(statistics.stdev(values), 2) if len(values) > 1 else 0,
                    'min': min(values),
                    'max': max(values),
                }
            except Exception:
                return {}
        
        # Role stats
        role_counts = list(role_distribution.values())
        role_stats = calculate_stats(role_counts)
        role_stats['total_roles'] = len(role_counts)
        if role_distribution:
            role_stats['most_common'] = max(role_distribution.items(), key=lambda x: x[1])[0]
        
        # Consultation status stats
        status_counts = [item['count'] for item in consultation_status_list]
        status_stats = calculate_stats(status_counts)
        status_stats['total_statuses'] = len(status_counts)
        
        # Monthly stats
        monthly_counts = [item['count'] for item in monthly_consultations]
        monthly_stats = calculate_stats(monthly_counts)
        if monthly_counts:
            monthly_stats['range'] = max(monthly_counts) - min(monthly_counts)
            monthly_stats['variance'] = round(statistics.variance(monthly_counts), 2) if len(monthly_counts) > 1 else 0
        
        # Doctor stats
        doctor_counts = [d['consultation_count'] for d in doctor_performance_list]
        doctor_stats = calculate_stats(doctor_counts)
        doctor_stats['total_doctors'] = len(doctor_counts)
        if doctor_counts:
            doctor_stats['range'] = max(doctor_counts) - min(doctor_counts)
        
        # Booked Services statistics (period-aware)
        booked_services_by_status = BookedService.objects.filter(
            booking_date__gte=period_start.date(), 
            booking_date__lt=period_end.date()
        ).values('status').annotate(count=Count('status'))
        booked_services_status_distribution = {item['status']: item['count'] for item in booked_services_by_status}
        
        booked_services_by_service = BookedService.objects.filter(
            booking_date__gte=period_start.date(), 
            booking_date__lt=period_end.date()
        ).values('service_name').annotate(count=Count('service_name'))
        booked_services_service_distribution = {item['service_name']: item['count'] for item in booked_services_by_service}
        
        # Top Performing Fields/Specializations (period-aware)
        fields_performance = Doctor.objects.filter(
            doctor_consultations__created_at__gte=period_start,
            doctor_consultations__created_at__lt=period_end
        ).values('specialization').annotate(
            total_consultations=Count('doctor_consultations')
        ).order_by('-total_consultations')[:15]
        
        fields_distribution = {item['specialization'] or 'Unknown': item['total_consultations'] or 0 for item in fields_performance}
        
        # Lab Results (period-aware)
        lab_results_data = []
        if period_type != 'monthly':
            for i in range(6):
                month_date = period_start - timedelta(days=30*i)
                month_data_start = month_date.replace(day=1)
                if month_date.month == 12:
                    month_data_end = (month_date.replace(year=month_date.year+1, month=1))
                else:
                    month_data_end = month_date.replace(month=month_date.month+1)
                count = LabResult.objects.filter(upload_date__gte=month_data_start, upload_date__lt=month_data_end).count()
                lab_results_data.append({'month': month_date.strftime('%Y-%m'), 'count': count})
        else:
            lab_results_data = [{
                'month': period_label,
                'count': LabResult.objects.filter(upload_date__gte=period_start, upload_date__lt=period_end).count()
            }]
        
        total_lab_results_period = LabResult.objects.filter(upload_date__gte=period_start, upload_date__lt=period_end).count()
        total_booked_services_period = BookedService.objects.filter(booking_date__gte=period_start.date(), booking_date__lt=period_end.date()).count()
        
        return JsonResponse({
            'period_type': period_type,
            'period_label': period_label,
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'role_distribution': role_distribution,
            'consultation_status': consultation_status_list,
            'monthly_consultations': monthly_consultations,
            'lab_results': lab_results_data,
            'doctor_performance': doctor_performance_list,
            'role_stats': role_stats,
            'status_stats': status_stats,
            'monthly_stats': monthly_stats,
            'doctor_stats': doctor_stats,
            'booked_services_status_distribution': booked_services_status_distribution,
            'booked_services_service_distribution': booked_services_service_distribution,
            'fields_distribution': fields_distribution,
            'total_lab_results': total_lab_results_period,
            'total_booked_services': total_booked_services_period,
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"error": str(e)}, status=500)
