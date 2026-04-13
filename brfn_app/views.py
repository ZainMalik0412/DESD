from django.shortcuts import render
from django.http import JsonResponse


def home(request):
    return render(request, 'home.html')

def terms(request):
    return render(request, "terms.html")

def health(request):
    return JsonResponse({"status": "ok"})