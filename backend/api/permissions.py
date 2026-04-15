from rest_framework.permissions import BasePermission

# Custom permission for athlete image service
class IsAthleteImageService(BasePermission):
    def has_permission(self, request, view):
        return request.auth.name == "athlete_image_service"