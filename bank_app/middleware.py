import logging
from django.shortcuts import render

logger = logging.getLogger(__name__)

class ExceptionHandlerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
       
        logger.error(f"Unhandled exception: {str(exception)}", exc_info=True)
        
    
        context = {'error': str(exception)}
        return render(request, '500.html', context, status=500)
