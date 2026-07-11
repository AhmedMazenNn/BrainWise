from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """Normalize all error responses to a consistent structure."""
    response = exception_handler(exc, context)

    if response is not None:
        if isinstance(response.data, dict):
            if 'detail' in response.data:
                response.data = {'detail': str(response.data['detail'])}
            else:
                response.data = {'detail': response.data}
        elif isinstance(response.data, list):
            response.data = {'detail': response.data[0] if response.data else 'Invalid request.'}

    return response
