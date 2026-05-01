from rest_framework.permissions import BasePermission
from rest_framework_api_key.models import APIKey

# Custom permission for athlete image service
class IsAthleteImageService(BasePermission):
    def has_permission(self, request, view):
        header = request.META.get("HTTP_AUTHORIZATION", "") # Get authorization header
        key = header.split()[1] # Extract API key from header (assuming format "Api-Key <key>")
        api_key = APIKey.objects.get_from_key(key) # Get APIKey object from key
        return api_key is not None and api_key.name == "athlete_image_service" # Check name of api to ensure it'c correct service

# Custom permission for uploader service
class IsUploaderService(BasePermission):
    def has_permission(self, request, view):
        header = request.META.get("HTTP_AUTHORIZATION", "") # Get authorization header
        key = header.split()[1] # Extract API key from header (assuming format "Api-Key <key>")
        api_key = APIKey.objects.get_from_key(key) # Get APIKey object from key
        return api_key is not None and api_key.name == "uploader_service" # Check name of api to ensure it's the correct service