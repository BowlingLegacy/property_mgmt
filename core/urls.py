from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Add this line for login/logout/password reset
    path('accounts/', include('django.contrib.auth.urls')),

    # Your app
    path('', include('main.urls')),
]
