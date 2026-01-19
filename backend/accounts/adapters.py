# accounts/adapters.py
from allauth.account.adapter import DefaultAccountAdapter
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()

class EmailVerificationAdapter(DefaultAccountAdapter):
    """
        -   Extends allAuths allauth.account functions
    """
    def clean_email(self, email):
        """
            -   Extends clean_email from allauth to prevent email duplicates upon sign up
        """
        print('EMAIL VERIFICATION')
        # run allauth's existing logic first
        email = super().clean_email(email)

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Email already exists.")

        return email