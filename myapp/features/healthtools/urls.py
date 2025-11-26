from django.urls import path
from .views import health_tools

urlpatterns = [
	path('health-tools/', health_tools, name='health_tools'),
]


