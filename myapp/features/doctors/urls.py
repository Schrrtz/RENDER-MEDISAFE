from django.urls import path
from .views import (
    doctor_panel, update_doctor_profile, search_patients, patient_lab_results, 
    download_lab_result, live_appointment, start_live_consultation, 
    restart_live_consultation, update_consultation_data, complete_consultation, 
    create_prescription, sign_prescription, generate_prescription_pdf, upload_prescription_file,
    get_all_prescriptions, prescription_details, download_prescription
    , mark_notification_read
)

urlpatterns = [
	path('doctor/panel/', doctor_panel, name='doctor_panel'),
    path('doctor/api/update-profile/', update_doctor_profile, name='doctor_update_profile'),
    path('doctors/search-patients/', search_patients, name='search_patients'),
    path('doctors/patient-lab-results/<int:patient_id>/', patient_lab_results, name='patient_lab_results'),
    path('doctors/download-lab-result/<int:result_id>/', download_lab_result, name='doctor_download_lab_result'),
    path('doctors/live-appointment/', live_appointment, name='live_appointment'),
    
    # Live Consultation System URLs
    path('doctors/start-consultation/<int:appointment_id>/', start_live_consultation, name='start_live_consultation'),
    path('doctors/restart-consultation/<int:appointment_id>/', restart_live_consultation, name='restart_live_consultation'),
    path('doctors/update-consultation/<int:live_session_id>/', update_consultation_data, name='update_consultation_data'),
    path('doctors/complete-consultation/<int:live_session_id>/', complete_consultation, name='complete_consultation'),
    path('doctors/create-prescription/<int:live_session_id>/', create_prescription, name='create_prescription'),
    path('doctors/sign-prescription/<int:prescription_id>/', sign_prescription, name='sign_prescription'),
    path('doctors/prescription-pdf/<int:prescription_id>/', generate_prescription_pdf, name='generate_prescription_pdf'),
    path('doctors/upload-prescription-file/<int:prescription_id>/', upload_prescription_file, name='upload_prescription_file'),
    path('api/get-all-prescriptions/', get_all_prescriptions, name='get_all_prescriptions'),
    path('doctors/prescription-details/<int:prescription_id>/', prescription_details, name='prescription_details'),
    path('doctors/download-prescription/<int:prescription_id>/', download_prescription, name='download_prescription'),
    path('doctors/api/mark-notification-read/', mark_notification_read, name='doctor_mark_notification_read'),
]


