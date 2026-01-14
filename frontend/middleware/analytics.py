# frontend/middleware/analytics.py

class AnalyticsMiddleware:
    """
    Middleware pour tracker les analytics (placeholder).
    À implémenter plus tard.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Code avant la vue
        # (tracking, logs, etc.)
        
        response = self.get_response(request)
        
        # Code après la vue
        # (mesure temps de réponse, etc.)
        
        return response