from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.db import IntegrityError, transaction, connection
from django.contrib.auth import login as auth_login, authenticate, logout as auth_logout
from django.middleware.csrf import get_token
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from datetime import datetime
from django.utils import timezone
import os
import json
import logging

from ...models import User, UserProfile, Patient, Notification

logger = logging.getLogger(__name__)

@csrf_exempt
def login(request):
    if request.method == "POST":
        try:
            if not request.body:
                return JsonResponse({"message": "No data provided"}, status=400)
            
            data = json.loads(request.body)
            username = data.get("username")
            password = data.get("password")
            
            # Secret admin login (dev-only, controlled by env)
            allow_backdoor = os.getenv('ALLOW_DEV_ADMIN_LOGIN', 'True').lower() in ('1','true','yes','on')
            if allow_backdoor and username == "CHOWKING" and password == "MEDISAFE":
                request.session["is_admin"] = True
                request.session["username"] = "Administrator"
                return JsonResponse({
                    "message": "Login successful",
                    "redirect": "/moddashboard",
                    "csrftoken": get_token(request)
                })
            
            # First try to authenticate the user
            user = authenticate(username=username, password=password)
            if user is not None:
                # Check if account is deactivated (status=False)
                if not user.status:
                    return JsonResponse({
                        "message": "Account Deactivated",
                        "detail": "Your account has been deactivated. Please contact the administrator for assistance.",
                        "is_deactivated": True,
                        "contact_email": "admin@medisafe.com"
                    }, status=403)
                
                if user.is_active:
                    # User is valid, active and authenticated
                    auth_login(request, user)
                    
                    # Set up the session
                    request.session.set_expiry(86400)  # 24 hours
                    request.session['user'] = user.user_id
                    request.session['user_id'] = user.user_id  # For admin views compatibility
                    request.session['role'] = user.role
                    
                    # Get user's display name
                    user_profile = UserProfile.objects.filter(user=user).first()
                    display_name = user.username
                    if user_profile:
                        if user_profile.first_name:
                            display_name = user_profile.first_name
                            if user_profile.last_name:
                                display_name += f" {user_profile.last_name}"
                    
                    # Create welcome message
                    welcome_msg = f"Welcome back, {display_name}!"
                    
                    # Redirect based on role
                    if user.role == "doctor":
                        redirect_url = "/doctor/panel/"
                    elif user.role == "patient":
                        redirect_url = "/dashboard"
                    else:
                        redirect_url = "/moddashboard"

                    return JsonResponse({
                        "message": "Login successful",
                        "welcome_message": welcome_msg,
                        "user_name": display_name,
                        "user_role": user.role,
                        "redirect": redirect_url,
                        "csrftoken": get_token(request)
                    })
                else:
                    return JsonResponse({"message": "Your account is not active. Please contact support."}, status=403)
            else:
                return JsonResponse({"message": "Invalid username or password"}, status=401)
        except Exception as e:
            return JsonResponse({"message": str(e)}, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({"message": "Invalid JSON"}, status=400)
    
    return JsonResponse({"message": "Method not allowed"}, status=405)

@csrf_exempt
def signup(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get("username")
            email = data.get("email")
            password = data.get("password")
            first_name = data.get("first_name", "")
            last_name = data.get("last_name", "")
            middle_name = data.get("middle_name", "")
            sex = data.get("sex", "")
            birthday = data.get("birthday", "")
            civil_status = data.get("civil_status", "")
            address = data.get("address", "")
            contact_person = data.get("contact_person", "")
            relationship_to_patient = data.get("relationship_to_patient", "")
            contact_number = data.get("contact_number", "")
            phone_number = data.get("phone_number", "")
            phone_type = data.get("phone_type", "")
            data_privacy_consent = data.get("data_privacy_consent", False)
            role = data.get("role", "patient")

            # Normalize the email address
            email = email.lower().strip()

            # Direct database verification using raw SQL
            with connection.cursor() as cursor:
                # Check for exact email match
                cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(email) = LOWER(%s)", [email])
                email_count = cursor.fetchone()[0]
                
                # Check for exact username match
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", [username])
                username_count = cursor.fetchone()[0]

                logger.debug(f"Email count for {email}: {email_count}")
                logger.debug(f"Username count for {username}: {username_count}")

                if username_count > 0:
                    return JsonResponse({
                        "message": "Username already exists",
                        "field": "username"
                    }, status=400)
                
                if email_count > 0:
                    return JsonResponse({
                        "message": "Email address already exists",
                        "field": "email"
                    }, status=400)

            # If we reach here, the email and username are unique
            try:
                with transaction.atomic():
                    # Double-check one more time inside transaction
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT COUNT(*) FROM users WHERE LOWER(email) = LOWER(%s) OR username = %s", [email, username])
                        if cursor.fetchone()[0] > 0:
                            raise IntegrityError("User with this email or username already exists")

                    # Create the user
                    user = User(
                        username=username,
                        email=email,
                        password=password,  # This will be hashed in the save() method
                        role=role
                    )
                    user.save()  # This will hash the password
                    
                    # Parse birthday to date if provided
                    birthday_date = None
                    if birthday:
                        try:
                            birthday_date = datetime.strptime(birthday, '%Y-%m-%d').date()
                        except (ValueError, TypeError):
                            logger.error(f"Invalid birthday format: {birthday}")
                            birthday_date = None
                    
                    # Create associated profile with all fields
                    UserProfile.objects.create(
                        user=user,
                        first_name=first_name,
                        last_name=last_name,
                        middle_name=middle_name if middle_name else None,
                        sex=sex if sex else None,
                        birthday=birthday_date,
                        civil_status=civil_status if civil_status else None,
                        address=address if address else None,
                        contact_person=contact_person if contact_person else None,
                        relationship_to_patient=relationship_to_patient if relationship_to_patient else None,
                        contact_number=contact_number if contact_number else None,
                        phone_number=phone_number if phone_number else None,
                        phone_type=phone_type if phone_type else None,
                        data_privacy_consent=data_privacy_consent,
                        consent_date=timezone.now() if data_privacy_consent else None
                    )
                    
                    # Note: Don't create Patient record - it's optional and causes database errors
                    # if role == "patient":
                    #     Patient.objects.create(user=user)

                    # Login the user automatically
                    user.backend = 'django.contrib.auth.backends.ModelBackend'
                    auth_login(request, user)
                    request.session['user'] = user.user_id
                    request.session['user_id'] = user.user_id  # For admin views compatibility
                    request.session['role'] = user.role

                    # Verify the user was actually created
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = %s", [user.user_id])
                        if cursor.fetchone()[0] != 1:
                            raise Exception("User creation verification failed")

                    return JsonResponse({
                        "message": "Account successfully created! Logging you in...",
                        "success": True,
                        "redirect": "/dashboard"
                    }, status=200)

            except IntegrityError as e:
                logger.error(f"IntegrityError during registration: {str(e)}")
                error_message = str(e).lower()
                if 'email' in error_message:
                    return JsonResponse({
                        "message": "This email address is already registered.",
                        "field": "email",
                        "success": False
                    }, status=400)
                elif 'username' in error_message:
                    return JsonResponse({
                        "message": "This username is already taken.",
                        "field": "username",
                        "success": False
                    }, status=400)
                else:
                    return JsonResponse({
                        "message": "An error occurred during registration. Please try again.",
                        "success": False
                    }, status=400)

            except Exception as e:
                logger.error(f"Unexpected error during registration: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return JsonResponse({
                    "message": f"An unexpected error occurred: {str(e)}",
                    "success": False
                }, status=500)

        except json.JSONDecodeError:
            return JsonResponse({
                "message": "Invalid request format",
                "success": False
            }, status=400)
    
    return JsonResponse({
        "message": "Method not allowed"
    }, status=405)

def logout(request):
    auth_logout(request)
    # Clear all session data
    request.session.flush()
    messages.success(request, "You have been logged out successfully")
    return redirect("homepage2")

@csrf_exempt
def update_profile(request):
    if request.method != "POST":
        return JsonResponse({"message": "Method not allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"message": "Invalid JSON"}, status=400)

    # Check if user is logged in
    user_id = request.session.get("user")
    if not user_id:
        return JsonResponse({"message": "Not logged in"}, status=401)

    try:
        # Get the user and their profile
        user = User.objects.get(user_id=user_id)
        profile = UserProfile.objects.get(user=user)

        # Update profile fields
        if "first_name" in data:
            profile.first_name = data["first_name"]
        if "last_name" in data:
            profile.last_name = data["last_name"]
        if "email" in data:
            # Check if email is already used by another user
            if User.objects.filter(email=data["email"]).exclude(user_id=user_id).exists():
                return JsonResponse({"message": "Email already in use"}, status=400)
            user.email = data["email"]
        if "phone" in data:
            profile.phone = data["phone"]
        if "date_of_birth" in data and data["date_of_birth"]:
            try:
                profile.date_of_birth = datetime.strptime(data["date_of_birth"], "%Y-%m-%d").date()
            except ValueError:
                return JsonResponse({"message": "Invalid date format"}, status=400)
        if "bio" in data:
            profile.bio = data["bio"]
        if "address" in data:
            profile.address = data["address"]
        if "gender" in data:
            profile.gender = data["gender"]

        # Use transaction to ensure both saves succeed or neither does
        with transaction.atomic():
            user.save()
            profile.save()

        return JsonResponse({
            "message": "Profile updated successfully",
            "success": True
        })

    except (User.DoesNotExist, UserProfile.DoesNotExist):
        return JsonResponse({"message": "User or profile not found"}, status=404)
    except Exception as e:
        return JsonResponse({"message": str(e)}, status=500)


@csrf_exempt
def super_admin_login(request):
    """
    Authenticate as Super Admin with specific credentials.
    Credentials: 
    - Name: MEDISAFE
    - Password: ACDMSKINGS60
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            name = data.get("name", "").strip()
            password = data.get("password", "").strip()
            
            # Super Admin credentials
            SUPER_ADMIN_NAME = "MEDISAFE"
            SUPER_ADMIN_PASSWORD = "ACDMSKINGS60"
            
            # Validate credentials
            if name == SUPER_ADMIN_NAME and password == SUPER_ADMIN_PASSWORD:
                # Set session flags for Super Admin
                request.session["is_super_admin"] = True
                request.session["is_admin"] = True
                request.session["super_admin_username"] = "Super Administrator"
                request.session["role"] = "super_admin"
                
                return JsonResponse({
                    "success": True,
                    "message": "Super Admin authenticated successfully"
                })
            else:
                return JsonResponse({
                    "success": False,
                    "message": "Invalid Super Admin credentials"
                }, status=401)
                
        except json.JSONDecodeError:
            return JsonResponse({"message": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"message": str(e)}, status=500)
    
    return JsonResponse({"message": "Method not allowed"}, status=405)


@csrf_exempt
def check_super_admin_status(request):
    """
    Check if user is currently in Super Admin mode.
    """
    is_super_admin = request.session.get("is_super_admin", False)
    
    return JsonResponse({
        "is_super_admin": is_super_admin,
        "username": request.session.get("super_admin_username") if is_super_admin else None
    })


@csrf_exempt
def exit_super_admin(request):
    """
    Exit Super Admin mode while staying logged in as regular admin.
    Demotes user from Super Admin back to regular Admin.
    """
    if request.method == "POST":
        try:
            # Remove Super Admin session flags
            if "is_super_admin" in request.session:
                del request.session["is_super_admin"]
            if "super_admin_username" in request.session:
                del request.session["super_admin_username"]
            
            # Keep is_admin flag to remain logged in
            request.session["is_admin"] = True
            request.session["role"] = "admin"
            
            # Save session
            request.session.modified = True
            
            return JsonResponse({
                "success": True,
                "message": "Exited Super Admin mode. You remain logged as admin."
            })
        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": str(e)
            }, status=500)
    
    return JsonResponse({"message": "Method not allowed"}, status=405)


@csrf_exempt
def forgot_password(request):
    """Handle forgot password requests with ID photo verification"""
    if request.method != "POST":
        return JsonResponse({"message": "Method not allowed", "success": False}, status=405)
    
    try:
        username_or_email = request.POST.get('username_or_email', '').strip()
        id_photo = request.FILES.get('id_photo')
        contact_method = (request.POST.get('contact_method') or 'sms').strip().lower()
        if contact_method not in ('sms', 'email', 'messenger', 'facebook'):
            contact_method = 'sms'
        
        logger.info(f"Forgot password request received for: {username_or_email} via {contact_method}")
        
        if not username_or_email:
            return JsonResponse({
                "message": "Please provide username or email",
                "success": False
            }, status=400)
        
        if not id_photo:
            return JsonResponse({
                "message": "Please upload your ID photo for verification",
                "success": False
            }, status=400)
        
        # Validate file type
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
        if id_photo.content_type not in allowed_types:
            return JsonResponse({
                "message": "Invalid file type. Please upload a JPG, PNG, or GIF image.",
                "success": False
            }, status=400)
        
        # Validate file size (5MB max)
        if id_photo.size > 5 * 1024 * 1024:
            return JsonResponse({
                "message": "File size too large. Please upload an image smaller than 5MB.",
                "success": False
            }, status=400)
        
        # Try to find user by username or email
        user = None
        try:
            # Try username first
            user = User.objects.get(username=username_or_email)
            logger.info(f"User found by username: {user.user_id}")
        except User.DoesNotExist:
            try:
                # Try email
                user = User.objects.get(email__iexact=username_or_email)
                logger.info(f"User found by email: {user.user_id}")
            except User.DoesNotExist:
                logger.info(f"User not found for: {username_or_email}")
                pass
        
        if not user:
            # Don't reveal if user exists for security, but still return success message
            # This prevents user enumeration attacks
            return JsonResponse({
                "message": "If an account exists with that username or email, we have logged your request and will text your registered mobile number once it is reviewed.",
                "success": True
            })
        
        # Get all admin users (including super admin via session check)
        admin_users = User.objects.filter(role='admin', status=True, is_active=True)
        logger.info(f"Found {admin_users.count()} admin users to notify")
        
        if not admin_users.exists():
            logger.warning("No admin users found to send password reset notification")
            return JsonResponse({
                "message": client_success_message,
                "success": True
            })
        
        # Store the file temporarily to be used for multiple notifications
        from django.core.files.base import ContentFile
        file_content = id_photo.read()
        file_name = id_photo.name
        
        # Prepare contact method display (locked to SMS for now)
        contact_method_map = {
            'sms': 'SMS (Mobile Message)',
            'email': 'Email',
            'messenger': 'Messenger',
            'facebook': 'Facebook'
        }
        contact_display = contact_method_map.get(contact_method, 'SMS (Mobile Message)')
        if contact_method != 'sms':
            contact_display = contact_method_map['sms']
        
        # Get user profile for additional info
        user_profile = None
        try:
            user_profile = user.userprofile
        except Exception:
            user_profile = None
        if user_profile and user_profile.contact_number:
            sms_display = f"{user_profile.contact_number} (profile contact)"
        else:
            sms_display = "the patient's registered mobile number on file"
        
        # Build notification message with contact preference
        full_name = f"{user_profile.first_name} {user_profile.last_name}" if user_profile else user.username
        notification_message = (
            f"User <strong>{full_name}</strong> (Username: {user.username}, Email: {user.email}) "
            f"has requested a password reset.<br/>"
            f"<strong>Contact Preference:</strong> {contact_display}<br/>"
            f"<strong>SMS Target:</strong> {sms_display}.<br/>"
            f"<strong>Requested at:</strong> {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}<br/>"
            f"Patient expects an SMS confirmation only. Please verify their ID photo and assist with password recovery."
        )
        
        client_success_message = "Password reset request submitted successfully! Expect a confirmation text message once we verify your ID."

        # Create notification for each admin
        notification_count = 0
        for admin_user in admin_users:
            try:
                # Create a new ContentFile for each notification to avoid "file already read" error
                notification_file = ContentFile(file_content, name=file_name)
                notification = Notification.objects.create(
                    user=admin_user,
                    title=f"Password Reset Request - {full_name}",
                    message=notification_message,
                    notification_type='password_reset',
                    priority='high',
                    file=notification_file,
                    related_id=user.user_id  # Store the requesting user's ID
                )
                notification_count += 1
                logger.info(f"Created notification {notification.notification_id} for admin {admin_user.user_id} with related_id={user.user_id}")
            except Exception as e:
                logger.error(f"Error creating notification for admin {admin_user.user_id}: {str(e)}")
                continue
        
        logger.info(f"Successfully created {notification_count} notification(s) for password reset request from user {user.user_id}")
        
        return JsonResponse({
            "message": client_success_message,
            "success": True
        })
        
    except Exception as e:
        logger.error(f"Error in forgot_password: {str(e)}", exc_info=True)
        return JsonResponse({
            "message": "An error occurred while processing your request. Please try again later.",
            "success": False
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_account(request):
    """Verify if an account exists for password reset"""
    try:
        data = json.loads(request.body)
        username_or_email = data.get('username_or_email', '').strip()
        
        if not username_or_email:
            return JsonResponse({
                "success": False,
                "message": "Please provide username or email",
                "exists": False
            })
        
        # Try to find user by username or email
        user = None
        found_by = None
        try:
            user = User.objects.get(username=username_or_email)
            found_by = 'username'
        except User.DoesNotExist:
            try:
                user = User.objects.get(email__iexact=username_or_email)
                found_by = 'email'
            except User.DoesNotExist:
                pass
        
        if not user:
            return JsonResponse({
                "success": True,
                "message": "Account not found. Please check your username or email.",
                "exists": False
            })
        
        # Get user profile information
        try:
            profile = user.userprofile
            full_name = f"{profile.first_name} {profile.last_name}".strip()
        except:
            full_name = user.username
        
        return JsonResponse({
            "success": True,
            "message": f"Account found: {full_name}",
            "exists": True,
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "full_name": full_name,
            "found_by": found_by
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "message": "Invalid request format"
        }, status=400)
    except Exception as e:
        logger.error(f"Error in verify_account: {str(e)}", exc_info=True)
        return JsonResponse({
            "success": False,
            "message": "An error occurred during verification"
        }, status=500)


