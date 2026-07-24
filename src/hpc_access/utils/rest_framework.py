from rest_framework.pagination import CursorPagination as CursorPagination_


class CursorPagination(CursorPagination_):
    """Custom cursor pagination class."""

    page_size = 100
    ordering = "-date_created"
    cursor_query_param = "cursor"
    page_size_query_param = "page_size"
    max_page_size = 1000
    template = "rest_framework/pagination/previous_and_next.html"
