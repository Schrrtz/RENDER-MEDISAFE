from django.urls import path
from . import dashboard_views, analytics_views, patient_views, user_views, account_views, doctor_views, consultation_views

urlpatterns = [
    # Admin Dashboard
    path('moddashboard/', dashboard_views.moddashboard, name='moddashboard'),
    path('moddashboard/clear-activity/', dashboard_views.clear_recent_activity, name='clear_recent_activity'),
    path('get_notification_file/<int:notification_id>/', dashboard_views.get_notification_file, name='get_notification_file'),
    path('api/admin/password-reset-notifications/', dashboard_views.get_password_reset_notifications, name='get_password_reset_notifications'),
    path('api/admin/mark-password-reset-read/<int:notification_id>/', dashboard_views.mark_password_reset_read, name='mark_password_reset_read'),
    
    # Analytics
    path('analytics/', analytics_views.analytics, name='mod_analytics'),
    path('api/analytics/', analytics_views.analytics_api, name='analytics_api'),
    path('api/analytics/dynamic-stats/', analytics_views.get_dynamic_statistics, name='get_dynamic_statistics'),
    
    # Patient Records Management (formerly mod_patients)
    path('manage/patients/', patient_views.mod_patients, name='mod_records'),
    
    # User Management
    path('manage/users/', user_views.mod_users, name='mod_users'),
    path('api/password-reset-requests/<str:user_id>/', user_views.get_password_reset_requests, name='get_password_reset_requests'),
    path('api/password-reset-file/<int:notification_id>/', user_views.download_password_reset_file, name='download_password_reset_file'),
    path('api/download-password-reset-file/', user_views.download_password_reset_file, name='download_password_reset_file_query'),
    path('api/password-reset-mark-read/<int:notification_id>/', user_views.mark_password_reset_as_read, name='mark_password_reset_as_read'),
    
    # Account Management
    path('manage/accounts/', account_views.mod_accounts, name='mod_accounts'),
    path('manage/accounts/activate/<str:user_id>/', account_views.activate_account, name='activate_account'),
    path('manage/accounts/deactivate/<str:user_id>/', account_views.deactivate_account, name='deactivate_account'),
    path('manage/accounts/delete/<str:user_id>/', account_views.delete_account, name='delete_account'),
    
    # Doctor Management
    path('manage/doctors/', doctor_views.mod_doctors, name='mod_doctors'),
    # JSON/API endpoints for doctor management
    path('mod_doctors/get/<str:doctor_id>/', doctor_views.get_doctor_details, name='get_doctor_details'),
    path('mod_doctors/edit/<str:doctor_id>/', doctor_views.edit_doctor, name='edit_doctor'),
    path('mod_doctors/patients/<str:doctor_id>/', doctor_views.get_doctor_patients, name='get_doctor_patients'),
    path('mod_doctors/add-medisafe-member/', doctor_views.add_medisafe_member, name='add_medisafe_member'),
    path('mod_doctors/convert-member-to-patient/<str:user_id>/', doctor_views.convert_member_to_patient, name='convert_member_to_patient'),
    
    # Consultation Management
    path('manage/consultations/', consultation_views.mod_consultations, name='mod_consultations'),
    path('api/update-consultation-status/', consultation_views.update_consultation_status, name='update_consultation_status'),
    path('api/delete-consultation/', consultation_views.delete_consultation, name='delete_consultation'),
    path('api/get-consultation/', consultation_views.get_consultation_details, name='get_consultation_details'),
    path('api/save-consultation/', consultation_views.save_consultation, name='save_consultation'),
    
    # Booked Services API
    path('api/update-booked-service/', patient_views.update_booked_service, name='update_booked_service'),
    path('api/delete-booked-service/', patient_views.delete_booked_service, name='delete_booked_service'),
    path('api/patient-stats/<str:patient_id>/', patient_views.get_patient_stats, name='get_patient_stats'),
    
    # Prescription Management APIs
    path('api/admin-prescription-download/<int:prescription_id>/', patient_views.admin_prescription_download, name='admin_prescription_download'),
    path('api/admin-prescription-details/<int:prescription_id>/', patient_views.admin_prescription_details, name='admin_prescription_details'),
    path('api/delete-prescription/<int:prescription_id>/', patient_views.delete_prescription, name='delete_prescription'),
    
    # Lab Result Download API (for admins)
    path('api/download-lab-result/<int:result_id>/', patient_views.admin_lab_result_download, name='admin_lab_result_download'),
    # Send notification (admin -> user)
    path('api/send-notification/', patient_views.mod_patients, name='admin_send_notification'),
    
    # Permission Management API
    path('api/admin/permissions/', dashboard_views.manage_permissions, name='manage_permissions'),
]