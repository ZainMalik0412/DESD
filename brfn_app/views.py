from django.shortcuts import render


def home(request):
    return render(request, 'home.html')

def terms(request):
    return render(request, "terms.html")