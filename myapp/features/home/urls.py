from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage2, name='homepage2'),
    path('homepage2/', views.homepage2, name='homepage2_alt'),
]



