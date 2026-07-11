from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Shared pagination: 20 per page, configurable via query param, max 100."""

    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
