from django.http import JsonResponse


class HealthCheckMiddleware:
    """Respond to /health/ before ALLOWED_HOSTS validation.

    ALB health checks send the target's private IP as the Host header,
    which Django rejects with 400.  This middleware intercepts the
    health-check path early so it never reaches the host-validation layer.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/health/":
            return JsonResponse({"status": "ok"})
        return self.get_response(request)
