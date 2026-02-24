from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser
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
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        if CustomUser.objects.filter(username=username).exists():
            error = 'Username already taken.'
        else:
            user = CustomUser.objects.create_user(
                username=username, email=email, password=password, role=role
            )
            login(request, user)
            return redirect('/')
    return render(request, 'accounts/register.html', {'error': error})

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