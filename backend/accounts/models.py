from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    auth0_id = models.CharField(max_length=255, unique=True)
    username = models.CharField(max_length=255, unique=True)
    profile_complete = models.BooleanField(default=False)