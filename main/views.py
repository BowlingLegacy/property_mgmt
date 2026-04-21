from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from .forms import ApplicationForm
from .models import Application, UserProfile

# Homepage
def home(request):
    return render(request, 'main/home.html')

# Signup page
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user)
            return redirect('login')
    else:
        form = UserCreationForm()

    return render(request, 'registration/signup.html', {'form': form})

# Application form (logged-in users only)
@login_required
def apply(request):
    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.save()

            # update user status
            profile = UserProfile.objects.get(user=request.user)
            profile.status = 'submitted'
            profile.save()

            return redirect('application_submitted')
    else:
        form = ApplicationForm()

    return render(request, 'main/application.html', {'form': form})

# Application submitted confirmation page
def application_submitted(request):
    return render(request, 'main/application_submitted.html')

