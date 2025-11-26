from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from ..models import User

def login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this page")
            return redirect("homepage2")
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # First check if user is authenticated
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this page")
            return redirect("homepage2")
        
        # Then check if user is an admin
        if request.user.role != "admin":
            messages.error(request, "Unauthorized access")
            return redirect("homepage2")
            
        return view_func(request, *args, **kwargs)
    return wrapper

def doctor_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this page")
            return redirect("homepage2")
        
        if request.user.role != "doctor":
            messages.error(request, "Unauthorized access")
            return redirect("homepage2")
            
        return view_func(request, *args, **kwargs)
    return wrapper

def patient_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this page")
            return redirect("homepage2")
        
        if request.user.role != "patient":
            messages.error(request, "Unauthorized access")
            return redirect("homepage2")
            
        return view_func(request, *args, **kwargs)
    return wrapper