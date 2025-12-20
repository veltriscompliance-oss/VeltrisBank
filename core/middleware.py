class SecurityHeadersMiddleware:
    """
    Middleware to inject 'X-Robots-Tag' headers into all responses.
    This tells search engines and security bots that this site is 
    a private development environment.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Technically enforces that the site is private
        response['X-Robots-Tag'] = 'noindex, nofollow, noarchive'
        
        # Additional professional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        
        return response