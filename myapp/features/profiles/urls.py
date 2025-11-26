from django.urls import path
from . import views

urlpatterns = [
    path('userprofile/', views.userprofile, name='userprofile'),
    path('api/update-profile-photo/', views.update_profile_photo, name='update_profile_photo'),
    path('api/update-cover-photo/', views.update_cover_photo, name='update_cover_photo'),
    path('api/update-profile/', views.update_profile, name='update_profile'),
    path('api/update-profile-photo-legacy/', views.update_profile_photo_legacy, name='update_profile_photo_legacy'),
]
