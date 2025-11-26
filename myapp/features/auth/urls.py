from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login, name='login'),
    path('signup/', views.signup, name='signup'),
    path('logout/', views.logout, name='logout'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('super-admin-login/', views.super_admin_login, name='super_admin_login'),
    path('check-super-admin-status/', views.check_super_admin_status, name='check_super_admin_status'),
    path('exit-super-admin/', views.exit_super_admin, name='exit_super_admin'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('verify-account/', views.verify_account, name='verify_account'),
]



