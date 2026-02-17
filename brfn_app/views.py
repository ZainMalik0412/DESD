from django.shortcuts import render


def home(request):
    """Home page for the Bristol Regional Food Network marketplace."""
    return render(request, 'home.html')
