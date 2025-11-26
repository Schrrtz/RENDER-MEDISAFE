from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from ...models import User, UserProfile

def mod_accounts(request):
    """Account management view"""
    # Check for admin session first
    if request.session.get("is_admin"):
        # Get account statistics
        total_accounts = User.objects.count()
        active_accounts = User.objects.filter(status=True).count()
        inactive_accounts = User.objects.filter(status=False).count()

        # Get recent activity (last 5 user creations/modifications)
        recent_accounts = User.objects.order_by('-date_joined')[:5]

        context = {
            'total_accounts': total_accounts,
            'active_accounts': active_accounts,
            'inactive_accounts': inactive_accounts,
            'accounts': recent_accounts,  # Changed from recent_accounts to accounts
        }
        return render(request, "mod_accounts.html", context)
    
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

        # Get account statistics
        total_accounts = User.objects.count()
        active_accounts = User.objects.filter(status=True).count()
        inactive_accounts = User.objects.filter(status=False).count()

        # Get recent activity (last 5 user creations/modifications)
        recent_accounts = User.objects.order_by('-date_joined')[:5]

        context = {
            'total_accounts': total_accounts,
            'active_accounts': active_accounts,
            'inactive_accounts': inactive_accounts,
            'accounts': recent_accounts,  # Changed from recent_accounts to accounts
        }

    except User.DoesNotExist:
        messages.error(request, "User not found")
        return redirect("homepage2")
        
    return render(request, "mod_accounts.html", context)

@require_POST
def activate_account(request, user_id):
    """Activate a user account"""
    if not request.session.get("is_admin"):
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        user = get_object_or_404(User, user_id=user_id)
        user.status = True
        user.is_active = True
        user.save()
        
        return JsonResponse({
            "success": True,
            "message": f"Account {user.username} has been activated successfully."
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Error activating account: {str(e)}"
        }, status=400)

@require_POST
def deactivate_account(request, user_id):
    """Deactivate a user account"""
    if not request.session.get("is_admin"):
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        user = get_object_or_404(User, user_id=user_id)
        user.status = False
        user.is_active = False
        user.save()
        
        return JsonResponse({
            "success": True,
            "message": f"Account {user.username} has been deactivated successfully."
        })
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Error deactivating account: {str(e)}"
        }, status=400)

@require_POST
def delete_account(request, user_id):
    """Delete a user account"""
    if not request.session.get("is_admin"):
        return JsonResponse({"error": "Unauthorized"}, status=403)
    
    try:
        user = get_object_or_404(User, user_id=user_id)
        username = user.username
        
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                # Delete related records in the correct order
                tables = [
                    ('user_profiles', 'user_id'),
                    ('doctors', 'user_id'),
                    ('patients', 'user_id'),
                    ('users', 'user_id')
                ]
                
                for table, id_column in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {id_column} = %s", [user_id])
                        count = cursor.fetchone()[0]
                        if count > 0:
                            cursor.execute(f"DELETE FROM {table} WHERE {id_column} = %s", [user_id])
                    except Exception as table_error:
                        continue
            
            return JsonResponse({
                "success": True,
                "message": f"Account {username} has been deleted successfully."
            })
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print("Error details:", error_details)
            return JsonResponse({
                "success": False,
                "error": f"Error deleting account: {str(e)}"
            }, status=400)
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"Account not found: {str(e)}"
        }, status=404)
