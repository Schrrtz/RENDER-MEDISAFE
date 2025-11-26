from django.shortcuts import render, redirect

def homepage2(request):
    # Redirect to Homepage (formerly dashboard)
    return redirect('dashboard')


## removed temporary conditions view; handled by features.conditions.views
