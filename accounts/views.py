from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser
from .forms import CustomerRegistrationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

# PAGE VIEWS

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('/')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('/')


def register(request):
    error = None
    success = None

    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('/')
        else:
            error = 'Please correct the errors below.'
    else:
        form = CustomerRegistrationForm()

    return render(request, 'accounts/register.html', {
        'form': form,
        'error': error,
        'success': success,
    })

@login_required
def transaction_history(request):
    """View transaction history page - displays user's past transactions."""
    pass


@login_required
def current_orders(request):
    """View current/in-progress orders page."""
    pass

# HELPER FUNCTIONS

def authorise(user, action):
    """
    Checks if user has permission to perform action.
    Will use postgres for permission checking.
    
    Note: Consider moving to a separate utils.py or permissions.py file.
    """
    pass

def login_helper(user):
    """Login helper function."""
    pass

def logout_helper(user):
    """Logout helper function."""
    pass

def register_helper(user):
    """Register helper function."""
    pass