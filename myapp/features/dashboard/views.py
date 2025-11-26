from django.shortcuts import render, redirect
from django.contrib import messages

def dashboard(request):
    """Client-facing homepage for regular users"""
    user_id = request.session.get("user_id") or request.session.get("user")
    is_logged_in = user_id is not None
    
    # Pass user object for template authentication checks
    context = {
        "is_logged_in": is_logged_in,
        "user_id": user_id if is_logged_in else None,
        "user": request.user if hasattr(request, 'user') else None
    }
    
    return render(request, "Homepage.html", context)