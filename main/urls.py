from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('apply/', views.apply, name='apply'),
    path('application-submitted/', views.application_submitted, name='application_submitted'),
    path('signup/', views.signup, name='signup'),
]
