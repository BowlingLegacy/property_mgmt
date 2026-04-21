from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from .forms import ApplicationForm
from .models import Application, Property, OwnerProfile, Resident

# Property list (homepage)
def property_list(request):
    properties = Property.objects.all()
    return render(request, 'main/property_list.html', {'properties': properties})

# Property detail page
def property_detail(request, slug):
    property_obj = get_object_or_404(Property, slug=slug)
    return render(request, 'main/property_detail.html', {'property': property_obj})

# Signup page
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # later we can decide if this user is an owner or resident
            return redirect('login')
    else:
        form = UserCreationForm()

    return render(request, 'registration/signup.html', {'form': form})

# Application form for a specific property
@login_required
def apply_for_property(request, slug):
    property_obj = get_object_or_404(Property, slug=slug)

    if request.method == 'POST':
        form = ApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.property = property_obj
            application.save()
            return redirect('application_submitted')
    else:
        form = ApplicationForm()

    return render(request, 'main/application.html', {
        'form': form,
        'property': property_obj,
    })

# Application submitted confirmation page
def application_submitted(request):
    return render(request, 'main/application_submitted.html')

