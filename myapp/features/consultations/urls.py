from django.urls import path
from . import views

urlpatterns = [
    path('consultations/', views.consultations, name='consultations'),
    path('api/book-consultation/', views.book_consultation, name='book_consultation'),
    path('api/book-consultation-guest/', views.book_consultation_guest, name='book_consultation_guest'),
    path('api/create-appointment/', views.create_appointment, name='create_appointment'),
    path('api/cancel-consultation/', views.cancel_consultation, name='cancel_consultation'),
    path('api/get-consultation-details/<int:consultation_id>/', views.get_consultation_details, name='get_consultation_details'),
]