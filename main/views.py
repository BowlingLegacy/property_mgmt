from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required

# Homepage
def home(request):
    return render(request, 'main/home.html')

# Signup page
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # send user to login page after successful signup
    else:
        form = UserCreationForm()

    return render(request, 'registration/signup.html', {'form': form})

