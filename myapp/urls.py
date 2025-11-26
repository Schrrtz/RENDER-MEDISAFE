from django.urls import path, include

urlpatterns = [
    # Home feature
    path('', include('myapp.features.home.urls')),
    
    # Authentication feature
    path('', include('myapp.features.auth.urls')),
    
    # Dashboard feature
    path('', include('myapp.features.dashboard.urls')),
    
    # Consultations feature
    path('', include('myapp.features.consultations.urls')),
    
    # Profiles feature
    path('', include('myapp.features.profiles.urls')),
    
    # Patients feature
    path('', include('myapp.features.patients.urls')),
    
    # Medical feature
    path('', include('myapp.features.medical.urls')),
    
    # Health tools feature
    path('', include('myapp.features.healthtools.urls')),
    
    # Conditions feature
    path('', include('myapp.features.conditions.urls')),
    
    # Doctors feature
    path('', include('myapp.features.doctors.urls')),
    
    # Admin feature (admin/employee panels)
    path('', include('myapp.features.admin.urls')),
    
    # Legacy API endpoints removed - use feature-specific endpoints instead
]