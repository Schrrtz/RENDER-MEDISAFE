from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, FileResponse
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from ...models import User, UserProfile, Notification
import json
import os


def _get_session_admin_user(request):
    """Return the logged-in user object if available."""
    session_user_id = request.session.get("user_id") or request.session.get("user")
    if not session_user_id:
        return None
    try:
        return User.objects.get(user_id=session_user_id)
    except User.DoesNotExist:
        return None

def mod_users(request):
    """User management view"""
    # Check for admin session first
    if request.session.get("is_admin"):
        if request.method == 'POST':
            action = request.POST.get('action')
            
            if action == 'add':
                # Get form data
                username = request.POST.get('username')
                email = request.POST.get('email')
                role = request.POST.get('role')
                password = request.POST.get('password')
                sex = request.POST.get('sex', '')
                birthday = request.POST.get('birthday', '')
                first_name = request.POST.get('first_name', '')
                last_name = request.POST.get('last_name', '')
                middle_name = request.POST.get('middle_name', '')
                address = request.POST.get('address', '')
                contact_number = request.POST.get('contact_number', '')
                civil_status = request.POST.get('civil_status', '')

                if not all([username, email, role, password]):
                    messages.error(request, "All fields are required")
                    return redirect('mod_users')

                try:
                    # Start with is_active=True for new users
                    new_user = User.objects.create(
                        username=username,
                        email=email,
                        role=role,
                        is_active=True,
                        first_name=first_name,
                        last_name=last_name
                    )
                    new_user.set_password(password)
                    new_user.save()

                    # Create UserProfile for all users
                    UserProfile.objects.create(
                        user=new_user,
                        sex=sex,
                        birthday=birthday if birthday else None,
                        middle_name=middle_name,
                        address=address,
                        contact_number=contact_number,
                        civil_status=civil_status
                    )
                    
                    messages.success(request, f"{role.capitalize()} added successfully!")
                except IntegrityError:
                    messages.error(request, "Username or email already exists")
                except Exception as e:
                    # If any error occurs during user creation, cleanup
                    if 'new_user' in locals():
                        new_user.delete()
                    messages.error(request, f"Error adding user: {str(e)}")

            elif action == 'edit':
                user_id = request.POST.get('user_id')
                if not user_id:
                    messages.error(request, "No user specified for editing")
                    return redirect('mod_users')

                try:
                    user_to_edit = User.objects.get(user_id=user_id)
                    # Update user fields
                    user_to_edit.username = request.POST.get('username', user_to_edit.username)
                    user_to_edit.email = request.POST.get('email', user_to_edit.email)
                    user_to_edit.role = request.POST.get('role', user_to_edit.role)
                    
                    # Update password if provided
                    new_password = request.POST.get('password')
                    if new_password and new_password.strip():
                        user_to_edit.set_password(new_password)
                    
                    # Update account status if provided
                    status_value = request.POST.get('status')
                    if status_value:
                        is_active_flag = True if status_value == 'active' else False
                        user_to_edit.is_active = is_active_flag
                        # Keep model.status in sync when present
                        if hasattr(user_to_edit, 'status'):
                            user_to_edit.status = is_active_flag
                    
                    user_to_edit.save()

                    # Update or create UserProfile with ALL fields
                    profile, created = UserProfile.objects.get_or_create(user=user_to_edit)
                    
                    # Update all profile fields
                    profile.first_name = request.POST.get('first_name', profile.first_name)
                    profile.middle_name = request.POST.get('middle_name', profile.middle_name)
                    profile.last_name = request.POST.get('last_name', profile.last_name)
                    profile.sex = request.POST.get('sex', profile.sex)
                    profile.contact_number = request.POST.get('contact_number', profile.contact_number)
                    # 'emergency_contact' field renamed to 'contact_person' in migrations; map accordingly
                    contact_person = request.POST.get('contact_person')
                    if contact_person is None:
                        contact_person = request.POST.get('emergency_contact')  # backward compatibility
                    if contact_person is not None:
                        profile.contact_person = contact_person
                    profile.address = request.POST.get('address', profile.address)
                    profile.civil_status = request.POST.get('civil_status', profile.civil_status)
                    
                    # Handle birthday
                    birthday = request.POST.get('birthday')
                    if birthday:
                        try:
                            from datetime import datetime
                            profile.birthday = datetime.strptime(birthday, '%Y-%m-%d').date()
                        except (ValueError, TypeError):
                            pass
                    
                    profile.save()

                    messages.success(request, f"User '{user_to_edit.username}' updated successfully!")
                except User.DoesNotExist:
                    messages.error(request, "User not found")
                except IntegrityError:
                    messages.error(request, "Username or email already exists")
                except Exception as e:
                    messages.error(request, f"Error updating user: {str(e)}")
                
            elif action == 'delete':
                user_id_to_delete = request.POST.get('user_id')
                if not user_id_to_delete:
                    messages.error(request, "No user specified for deletion")
                    return redirect('mod_users')

                try:
                    user_to_delete = User.objects.get(user_id=user_id_to_delete)
                    username = user_to_delete.username  # Store for message
                    user_to_delete.delete()
                    messages.success(request, f"User '{username}' deleted successfully!")
                except User.DoesNotExist:
                    messages.error(request, "User not found")
                except Exception as e:
                    messages.error(request, f"Error deleting user: {str(e)}")

            elif action == 'toggle_status':
                user_id_to_toggle = request.POST.get('user_id')
                if not user_id_to_toggle:
                    messages.error(request, "No user specified for status toggle")
                    return redirect('mod_users')

                try:
                    user_to_toggle = User.objects.get(user_id=user_id_to_toggle)
                    user_to_toggle.is_active = not user_to_toggle.is_active
                    user_to_toggle.save()
                    status = "activated" if user_to_toggle.is_active else "deactivated"
                    messages.success(request, f"User '{user_to_toggle.username}' {status} successfully!")
                except User.DoesNotExist:
                    messages.error(request, "User not found")
                except Exception as e:
                    messages.error(request, f"Error toggling user status: {str(e)}")

            else:
                messages.error(request, "Invalid action specified")

        # Get all users with their profiles
        users = User.objects.all().select_related('userprofile').order_by('username')
        
        # Stats
        total_users_count = User.objects.count()
        active_users_count = User.objects.filter(is_active=True).count()
        inactive_users_count = User.objects.filter(is_active=False).count()

        # Account summaries (reuse logic from mod_accounts)
        total_accounts = User.objects.count()
        # Some code uses `status` field for accounts, others use `is_active`.
        # Safely compute active/inactive counts using whichever field exists.
        if hasattr(User, 'status'):
            active_accounts = User.objects.filter(status=True).count()
            inactive_accounts = User.objects.filter(status=False).count()
        else:
            active_accounts = User.objects.filter(is_active=True).count()
            inactive_accounts = User.objects.filter(is_active=False).count()

        all_accounts = User.objects.order_by('-date_joined')

        context = {
            'users': users,
            'user_roles': ['admin', 'staff', 'patient'],  # Available roles for dropdown
            'total_users_count': total_users_count,
            'active_users_count': active_users_count,
            'inactive_users_count': inactive_users_count,
            'total_accounts': total_accounts,
            'active_accounts': active_accounts,
            'inactive_accounts': inactive_accounts,
            'accounts': all_accounts,
            'all_accounts': all_accounts,
        }
        return render(request, "user_management.html", context)
    
    # Check for regular admin user
    user_id = request.session.get("user_id") or request.session.get("user")
    if not user_id:
        messages.error(request, "Please login first")
        return redirect("homepage2")
    
    try:
        admin = User.objects.get(user_id=user_id)
        if admin.role != 'admin':
            messages.error(request, "Access denied. Admin privileges required.")
            return redirect("homepage2")

        # Duplicate POST handling for regular admin users (same as above)
        if request.method == 'POST':
            action = request.POST.get('action')
            # ... rest of POST handling identical to above ...
            pass

        # Get all users except current admin, with their profiles
        users = User.objects.exclude(user_id=user_id).select_related('userprofile').order_by('username')
        
        # Stats
        total_users_count = User.objects.count()
        active_users_count = User.objects.filter(is_active=True).count()
        inactive_users_count = User.objects.filter(is_active=False).count()

        # Account summaries
        total_accounts = User.objects.count()
        if hasattr(User, 'status'):
            active_accounts = User.objects.filter(status=True).count()
            inactive_accounts = User.objects.filter(status=False).count()
        else:
            active_accounts = User.objects.filter(is_active=True).count()
            inactive_accounts = User.objects.filter(is_active=False).count()

        all_accounts = User.objects.order_by('-date_joined')

        context = {
            'users': users,
            'current_admin_id': user_id,
            'user_roles': ['admin', 'staff', 'patient'],  # Available roles for dropdown
            'total_users_count': total_users_count,
            'active_users_count': active_users_count,
            'inactive_users_count': inactive_users_count,
            'total_accounts': total_accounts,
            'active_accounts': active_accounts,
            'inactive_accounts': inactive_accounts,
            'accounts': all_accounts,
            'all_accounts': all_accounts,
        }
        return render(request, "user_management.html", context)

    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect("homepage2")


@csrf_exempt
@require_http_methods(["GET"])
def download_password_reset_file(request, notification_id=None):
    """
    Download the ID photo file from a password reset request
    Supports both path parameter and query parameter
    """
    session_admin = _get_session_admin_user(request)
    if not (request.session.get("is_admin") or (session_admin and session_admin.role == 'admin')):
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    # Get notification_id from path parameter or query parameter
    if notification_id is None:
        notification_id = request.GET.get('notification_id')
    
    if not notification_id:
        return JsonResponse({"error": "Missing notification_id"}, status=400)
    
    try:
        notification = Notification.objects.get(notification_id=notification_id)
        
        if not notification.file:
            return JsonResponse({"error": "No file attached to this notification"}, status=404)
        
        file_path = notification.file.path
        
        if not os.path.exists(file_path):
            return JsonResponse({"error": "File not found on disk"}, status=404)
        
        response = FileResponse(open(file_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response
        
    except Notification.DoesNotExist:
        return JsonResponse({"error": "Notification not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def mark_password_reset_read(request, notification_id):
    """Mark a password reset notification as read"""
    session_admin = _get_session_admin_user(request)
    if not (request.session.get("is_admin") or (session_admin and session_admin.role == 'admin')):
        return JsonResponse({"error": "Unauthorized", "success": False}, status=403)
    
    try:
        notification = Notification.objects.get(notification_id=notification_id)
        notification.is_read = True
        notification.save()
        return JsonResponse({"success": True, "message": "Notification marked as read"})
    except Notification.DoesNotExist:
        return JsonResponse({"error": "Notification not found", "success": False}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e), "success": False}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_password_reset_requests(request, user_id):
    """
    API endpoint to get all password reset requests for a specific user
    Returns JSON list of password reset notifications with file info
    """
    session_admin = _get_session_admin_user(request)
    if not (request.session.get("is_admin") or (session_admin and session_admin.role == 'admin')):
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        # Verify user exists
        user = User.objects.get(user_id=user_id)
        
        # Get all password reset notifications for this user (across admins)
        notifications = Notification.objects.filter(
            notification_type='password_reset',
            related_id=user_id
        ).exclude(user=user).select_related('user').order_by('-created_at')
        
        data = {
            "success": True,
            "user_id": user_id,
            "username": user.username,
            "email": user.email,
            "total_requests": notifications.count(),
            "requests": []
        }
        
        for notification in notifications:
            request_data = {
                "notification_id": notification.notification_id,
                "title": notification.title,
                "message": notification.message,
                "created_at": notification.created_at.isoformat(),
                "is_read": notification.is_read,
                "priority": notification.priority,
                "has_file": bool(notification.file),
                "file_name": os.path.basename(notification.file.name) if notification.file else None,
                "file_url": f"/admin/api/password-reset-file/{notification.notification_id}/" if notification.file else None
            }
            data["requests"].append(request_data)
        
        return JsonResponse(data)
        
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found", "success": False}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e), "success": False}, status=500)
