from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.auth.hashers import make_password
from django.conf import settings

User = get_user_model()

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        If 'pending_signup' in session: create user from that data and attach social account.
        Otherwise, try to find an existing user by email and log them in.
        """
        email = getattr(sociallogin.user, "email", "") or sociallogin.account.extra_data.get("email", "")
        pending = request.session.pop("pending_signup", None)

        if pending:
            # Signup flow
            if not email:
                messages.error(request, "Google did not return an email address. Cannot complete signup.")
                raise ImmediateHttpResponse(redirect("/"))

            if User.objects.filter(email__iexact=email).exists():
                messages.error(request, "This email is already registered. Please log in instead.")
                raise ImmediateHttpResponse(redirect("/"))

            username = pending.get("username")
            password = pending.get("password")
            if not username or not password:
                messages.error(request, "Signup data expired. Please try signing up again.")
                raise ImmediateHttpResponse(redirect("/"))

            extra = sociallogin.account.extra_data or {}
            first_name = sociallogin.user.first_name or extra.get("given_name") or extra.get("first_name") or ""
            last_name = sociallogin.user.last_name or extra.get("family_name") or extra.get("last_name") or ""

            # Create user
            user = User(username=username, email=email, first_name=first_name, last_name=last_name)
            user.password = make_password(password)
            user.save()

            # Attach the social account to the newly created user
            try:
                sociallogin.connect(request, user)
            except Exception:
                user.delete()
                messages.error(request, "Failed to attach social account. Please try again.")
                raise ImmediateHttpResponse(redirect("/"))

            # Log the user in
            backend = settings.AUTHENTICATION_BACKENDS[0]
            user.backend = backend
            auth_login(request, user)
            raise ImmediateHttpResponse(redirect("/dashboard/"))

        else:
            # Login flow: find existing user by provider email
            if not email:
                messages.error(request, "No email returned from Google. Please try another login method.")
                raise ImmediateHttpResponse(redirect("/"))

            try:
                user = User.objects.get(email__iexact=email)


                backend = settings.AUTHENTICATION_BACKENDS[0]
                user.backend = backend
                auth_login(request, user)
                raise ImmediateHttpResponse(redirect("/dashboard/"))
            except User.DoesNotExist:
                messages.error(request, "No account matches that Google email. Please sign up or try another login method.")
                raise ImmediateHttpResponse(redirect("/"))
