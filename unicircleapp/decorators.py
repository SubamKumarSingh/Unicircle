# accounts/decorators.py
from django.shortcuts import redirect
from functools import wraps
from django.http import HttpResponseForbidden

def session_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.session.get('is_admin') is True:
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("403 Forbidden: You are not allowed to access this page.")
    return wrapper
