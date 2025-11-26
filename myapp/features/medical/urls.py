from django.urls import path
from . import views

urlpatterns = [
    path('labresults/', views.lab_results, name='labresults'),
    path('labresults/view/<int:result_id>/', views.view_lab_result, name='view_lab_result'),
    path('labresults/download/<int:result_id>/', views.download_lab_result, name='download_lab_result'),
    path('labservices/book/', views.book_service, name='book-service'),
    path('labservices/details/', views.get_service_details, name='get-service-details'),
    path('vitals/', views.vitals, name='vitals'),
    path('alertnotification/', views.alertnotification, name='alertnotification'),
    path('alertnotification/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('alertnotification/dismiss/<int:notification_id>/', views.dismiss_notification, name='dismiss_notification'),
    path('prescriptions/', views.prescriptions, name='prescriptions'),
    path('prescription-print/<int:prescription_id>/', views.prescription_print, name='prescription_print'),
    path('prescription-view/<int:prescription_id>/', views.prescription_view, name='prescription_view'),
    path('prescription-details/<int:prescription_id>/', views.prescription_details, name='prescription_details'),
    path('prescription-download/<int:prescription_id>/', views.prescription_download, name='prescription_download'),
    # Global Notification API endpoints
    path('api/notifications/unread/', views.get_unread_notifications, name='get_unread_notifications'),
    path('api/notifications/mark-read/<int:notification_id>/', views.api_mark_notification_read, name='api_mark_notification_read'),
    path('api/notifications/password-reset/', views.get_password_reset_notifications, name='get_password_reset_notifications'),
]



