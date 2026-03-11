from rest_framework.pagination import PageNumberPagination


class FighterListPagination(PageNumberPagination):
	page_size = 100
	max_page_size = 100
	page_size_query_param = 'page_size'