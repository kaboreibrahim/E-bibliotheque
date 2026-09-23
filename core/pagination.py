"""
core/pagination.py
Pagination partagee par tous les ViewSets de l'API (PERF-003).
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200
