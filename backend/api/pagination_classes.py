from rest_framework.pagination import PageNumberPagination


class FighterListPagination(PageNumberPagination):
	'''
		Custom pagination class for fighter
	'''
	page_size = 100
	max_page_size = 100
	page_size_query_param = 'page_size'


class UserLeaguesPagination(PageNumberPagination):
	'''
		Custom pagination class for user leagues list
	'''
	page_size = 10
	max_page_size = 100
	page_size_query_param = 'page_size'