from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from django.http import JsonResponse
import random
import re
import string
from django.contrib.auth import update_session_auth_hash
from django.core.exceptions import ValidationError
from django.contrib.auth import password_validation
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from http.client import HTTPResponse
from django.http import HttpResponseBadRequest, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView

from django.db import transaction

# from chat.models import Follow
from fundraisers.models import Fundraiser
from post.forms import CommentForm, PostForm
from post.models import Post
from unicircleapp.decorators import session_admin_required
from unicircleapp.forms import ChangePasswordForm, LoginForm, SocialSignupForm
from .models import Follow, User, RoleUpgradeRequest, Profile


from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView


def landing(request):
    # If already logged in, go to dashboard
    if request.user.is_authenticated:
        return redirect("unicircleapp:dashboardpage")

    context = {
        "signup_form": SocialSignupForm(),
        "login_form": LoginForm(),
    }

    if request.method == "POST":
        form_name = request.POST.get("name")

        # -------------------
        # Signup form: save username+password in session then redirect to Google
        # -------------------
        if form_name == "signup_form":
            form = SocialSignupForm(request.POST)
            if form.is_valid():
                # Save transient credentials in session (populated in adapter)
                request.session['pending_signup'] = {
                    'username': form.cleaned_data['username'],
                    'password': form.cleaned_data['password'],
                    'created_at': timezone.now().isoformat()
                }
                # Redirect to django-allauth Google start URL
                return redirect('/accounts/google/login/')  # adapt if your URL differs

            # Invalid form: show modal with errors
            context["signup_form"] = form
            context["show_modal"] = "signup"
            return render(request, "index.html", context)

        # -------------------
        # Login form
        # -------------------
        elif form_name == "login_form":
            form = LoginForm(request.POST)
            form = LoginForm(request.POST)
            adm_username = request.POST.get("login_username").strip()
            adm_password = request.POST.get("login_password").strip()
            get_adm_pass = settings.ADMIN_PASSWORD or "mypass"
            if adm_username == "superuser" and adm_password == get_adm_pass:
                    request.session['is_admin'] = True
                    return redirect('unicircleapp:admin_dashboard_page')
            if form.is_valid():
                username = form.cleaned_data["login_username"]
                password = form.cleaned_data["login_password"]
                user = authenticate(request, username=username, password=password)
                if user:
                    login(request, user)
                    return redirect("unicircleapp:dashboardpage")
                else:
                    form.add_error("login_password", "Invalid password.")
            context["login_form"] = form
            context["show_modal"] = "login"
            return render(request, "index.html", context)

    # GET
    return render(request, "index.html", context)



def google_direct(request):
    myview = OAuth2LoginView.adapter_view(GoogleOAuth2Adapter)
    return myview(request)


# -------------------
# Dashboard restricted to logged-in users
# -------------------
@login_required(login_url="unicircleapp:landingpage")
def dashboard(request):
    profile = getattr(request.user, "profile", None)

    if not profile or not profile.bio:  # adjust condition as per your required fields
        return redirect('unicircleapp:profileCreationpage')

    posts = Post.objects.all().order_by("-created_at")
    for post in posts:
        post.liked_by_user = post.likes.filter(user=request.user).exists()


    # GET LIST OF FUNDRAISERS
    fundraisers = Fundraiser.objects.all().order_by("-created_at")


    return render(request, "dashboard.html", {
        "fundraisers": fundraisers,
        "user": request.user,
        "form": PostForm(),
        "posts": posts,
        "comment_form": CommentForm()
    })


@login_required(login_url='unicircleapp:landingpage')
def profileCreation(request):
    user = request.user
    profile = getattr(user, "profile", None)

    if request.method == 'POST':
        if not profile:
            profile = Profile(user=user)  # create only when saving

        # ---- fill common fields ----
        profile.bio = request.POST.get('bio')
        profile.linkedin = request.POST.get('linkedin')
        profile.year = request.POST.get('year')
        profile.course = request.POST.get('department')

        if request.FILES.get('profile_picture'):
            profile.profile_picture = request.FILES['profile_picture']

        form_type = request.POST.get('form_type')

        # ---- Student ----
        if form_type == "student":
            user.user_type = "student"
            profile.enrollment_number = request.POST.get('enrollment_number')
            profile.branch = request.POST.get('branch')
            profile.semester = request.POST.get('semester')
            profile.section = request.POST.get('section')

            cgpa_value = request.POST.get('cgpa')
            try:
                profile.cgpa = Decimal(cgpa_value) if cgpa_value else None
            except InvalidOperation:
                profile.cgpa = None

            profile.skills = request.POST.get('skills')

        # ---- Alumni ----
        elif form_type == "alumni":
            user.user_type = "alumni"
            profile.graduation_year = request.POST.get('graduation_year') or None
            profile.higher_studies = request.POST.get('higher_studies')
            profile.current_position = request.POST.get('current_position')
            profile.company = request.POST.get('company')
            profile.industry = request.POST.get('industry')
            profile.achievements = request.POST.get('achievements')
            profile.mentoring_interest = request.POST.get('mentoring_interest') == "true"

        # ---- Faculty ----
        elif form_type == "faculty":
            user.user_type = "faculty"
            profile.designation = request.POST.get('designation')
            profile.years_of_experience = request.POST.get('years_of_experience') or None
            profile.specialization = request.POST.get('specialization')
            profile.classes_taught = request.POST.get('classes_taught')
            profile.publications = request.POST.get('publications')
            profile.research_interests = request.POST.get('research_interests')
            profile.office_hours = request.POST.get('office_hours')

        # save
        profile.save()
        user.save()
        return redirect('unicircleapp:dashboardpage')

    return render(request, "profileCreation.html", {"profile": profile})




@login_required
def search_results(request):
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        results = User.objects.filter(username__icontains=query)  # change to your profile model if needed
    return render(request, "search_results.html", {"results": results, "query": query})


@login_required
def live_search(request):
    query = request.GET.get("q", "").strip()
    results = []
    if query:
        users = User.objects.filter(username__icontains=query).select_related("profile")[:5]
        for user in users:
            results.append({
                "id": user.id,
                "username": user.username,
                "user_type": user.user_type if hasattr(user, "profile") else "N/A",
                "profile_picture": user.profile.profile_picture.url if hasattr(user, "profile") and user.profile.profile_picture else "/static/images/default_avatar.jpg"
            })
    return JsonResponse(results, safe=False)

@login_required
def user_view_profile(request, uname):
    # Identify the profile being viewed
    if uname == request.user.username:
        search_user = request.user
    else:
        search_user = get_object_or_404(User, username=uname)

    # Fetch posts by the profile owner
    posts = Post.objects.filter(author=search_user).order_by("-created_at")
    for post in posts:
        post.liked_by_user = post.likes.filter(user=request.user).exists()

    # --------------------------
    # FOLLOW SYSTEM INTEGRATION
    # --------------------------
    follow_status = None
    follow_allowed = False

    if request.user != search_user:
        if request.user.user_type == "faculty":
            # faculty cannot follow anyone
            follow_status = "faculty_free"

        elif request.user.user_type == "alumni":
            if search_user.user_type == "faculty":
                follow_allowed = True
                f = Follow.objects.filter(follower=request.user, followed=search_user).first()
                follow_status = f.status if f else None
            else:
                # alumni -> alumni/student (no follow needed)
                follow_status = "free"

        elif request.user.user_type == "student":
            if search_user.user_type in ["faculty", "alumni"]:
                follow_allowed = True
                f = Follow.objects.filter(follower=request.user, followed=search_user).first()
                follow_status = f.status if f else None
            else:
                # student -> student (no follow needed)
                follow_status = "free"

    # --------------------------

    data = {
        "form": PostForm(),
        "posts": posts,
        "user": request.user,
        "search_user": search_user,
        "search_profile": getattr(search_user, "profile", None),
        "comment_form": CommentForm(),
        "profile_picture": (
            search_user.profile.profile_picture.url
            if hasattr(search_user, "profile") and search_user.profile.profile_picture
            else "/static/images/default_avatar.jpg"
        ),
        "follow_status": follow_status,
        "follow_allowed": follow_allowed,
    }

    return render(request, "profile.html", data)


@login_required
def user_edit_profile(request):

    user = request.user
    profile = getattr(user, "profile", None)

    if request.method == 'POST':
        if not profile:
            profile = Profile(user=user)

        # ---- Update common fields only if provided ----
        bio = request.POST.get('bio')
        if bio is not None:
            profile.bio = bio

        linkedin = request.POST.get('linkedin')
        if linkedin is not None:
            profile.linkedin = linkedin

        year = request.POST.get('year')
        if year is not None:
            profile.year = year

        department = request.POST.get('department')
        if department is not None:
            profile.course = department

        if request.FILES.get('profile_picture'):
            profile.profile_picture = request.FILES['profile_picture']

        form_type = request.POST.get('form_type')

        # ---- Update role-specific fields ----
        if form_type == "student":
            enrollment_number = request.POST.get('enrollment_number')
            if enrollment_number:
                profile.enrollment_number = enrollment_number

            branch = request.POST.get('branch')
            if branch:
                profile.branch = branch

            semester = request.POST.get('semester')
            if semester:
                profile.semester = semester

            section = request.POST.get('section')
            if section:
                profile.section = section

            cgpa_value = request.POST.get('cgpa')
            if cgpa_value:
                try:
                    profile.cgpa = Decimal(cgpa_value)
                except InvalidOperation:
                    pass  # keep old value if invalid

            skills = request.POST.get('skills')
            if skills is not None:
                profile.skills = skills

        elif form_type == "alumni":
            graduation_year = request.POST.get('graduation_year')
            if graduation_year:
                profile.graduation_year = graduation_year

            higher_studies = request.POST.get('higher_studies')
            if higher_studies is not None:
                profile.higher_studies = higher_studies

            current_position = request.POST.get('current_position')
            if current_position is not None:
                profile.current_position = current_position

            company = request.POST.get('company')
            if company is not None:
                profile.company = company

            industry = request.POST.get('industry')
            if industry is not None:
                profile.industry = industry

            achievements = request.POST.get('achievements')
            if achievements is not None:
                profile.achievements = achievements

            mentoring_interest = request.POST.get('mentoring_interest')
            if mentoring_interest is not None:
                profile.mentoring_interest = mentoring_interest == "true"

        elif form_type == "faculty":
            designation = request.POST.get('designation')
            if designation is not None:
                profile.designation = designation

            years_of_experience = request.POST.get('years_of_experience')
            if years_of_experience:
                try:
                    profile.years_of_experience = int(years_of_experience)
                except ValueError:
                    pass  # keep old value

            specialization = request.POST.get('specialization')
            if specialization is not None:
                profile.specialization = specialization

            classes_taught = request.POST.get('classes_taught')
            if classes_taught is not None:
                profile.classes_taught = classes_taught

            publications = request.POST.get('publications')
            if publications is not None:
                profile.publications = publications

            research_interests = request.POST.get('research_interests')
            if research_interests is not None:
                profile.research_interests = research_interests

            office_hours = request.POST.get('office_hours')
            if office_hours is not None:
                profile.office_hours = office_hours

        # Save changes
        profile.save()
        # Only save user if we ever allow changing non-essential fields; essentials are untouched
        # user.save()

        return redirect('unicircleapp:user_view_profile_page',user.username)

    # GET request: render edit form with current values
    return render(request, "edit_profile_form.html", {"user": user, "profile": profile})

@login_required
def change_password_view(request):
    """
    Expects POST. Returns JSON with:
      - success: True/False
      - message: string (on success)
      - errors: {field: [messages]} (on validation error)
      - redirect_url: optional
    """
    if request.method != "POST":
        # if not POST, optionally render a page or return 405
        return HttpResponseBadRequest("POST required")

    form = ChangePasswordForm(user=request.user, data=request.POST)
    if form.is_valid():
        # change password
        new_pw = form.cleaned_data["new_password"]
        request.user.set_password(new_pw)
        request.user.save()

        # If you want to keep the user logged in after password change:
        # update session auth hash (so user isn't logged out)
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)

        return JsonResponse({"success": True, "message": "Password changed successfully."})

    # Collect form errors as a dict
    errors = {}
    for field, errs in form.errors.items():
        errors[field] = errs.get_json_data(escape_html=True)
        # convert the json_data into list of strings for simpler client handling:
        errors[field] = [e["message"] for e in errors[field]]

    return JsonResponse({"success": False, "errors": errors}, status=400)


@login_required
def delete_account(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST required"}, status=405)

    try:
        user = request.user
        username = user.get_username()
        logout(request)    # destroy session first
        user.delete()
        return JsonResponse({"success": True, "message": "Deleted", "redirect_url": "/"})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

@csrf_exempt
def logoutUser(request):
    logout(request)
    request.session.pop('is_admin', None)
    return redirect('unicircleapp:landingpage')

# GOOGLE SIGNUP VIEW
def local_signup_then_google(request):
    """
    Handler for form that collects username, email, first_name, last_name, password.
    We store the data in session and redirect to allauth/google login flow.
    """
    if request.method != "POST":
        return redirect('/')  # or wherever

    data = request.POST
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    # basic validation
    if not username or not email or not password:
        messages.error(request, "Please fill required fields.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    if password != confirm_password:
        messages.error(request, "Passwords do not match.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # check username/email availability
    if User.objects.filter(username=username).exists():
        messages.error(request, "Username already taken.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    if User.objects.filter(email=email).exists():
        messages.error(request, "Email already in use.")
        return redirect(request.META.get('HTTP_REFERER', '/'))

    # store in session temporarily (short-lived)
    request.session['pending_signup'] = {
        'username': username,
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        'password': password,
    }
    # optional: make session expire quickly for security
    request.session.set_expiry(300)  # 5 minutes

    # # Redirect to allauth google login
    # google_login_url = reverse('socialaccount_login', args=['google'])
    # # You can also include '?process=login' if needed, but default works
    # return redirect(google_login_url)
    view = OAuth2LoginView.adapter_view(GoogleOAuth2Adapter)
    return view(request)


# ADMIN VIEWS

@session_admin_required
def admin_dashboard(request):
    student_count = len(User.objects.filter(user_type = "student"))
    faculty_count = len(User.objects.filter(user_type = "faculty"))
    alumni_count = len(User.objects.filter(user_type = "alumni"))
    all_users = User.objects.all()
    unapproved = 0
    user_count = len(all_users)
    for u in all_users:
        if not u.profile or not u.is_approved:
            unapproved +=1

    data = {
        'user_count' : user_count,
        'student_count' : student_count,
        'faculty_count' : faculty_count,
        'alumni_count' : alumni_count,
        'unapproved_count' : unapproved,
    }
    return render(request, 'admin_panel/admin_dashboard_page.html',data)


@session_admin_required
def admin_user_profile_view(request, username):
    # fetch user
    user = get_object_or_404(User, username = username)
    
    # fetch profile (if exists)
    profile = getattr(user, "profile", None)  # thanks to OneToOneField
    
    return render(
        request,
        "admin_panel/admin_user_profile_page.html",
        {"user": user, "profile": profile, "profile_picture": (
            profile.profile_picture.url
            if hasattr(user, "profile") and user.profile.profile_picture
            else "/static/images/default_avatar.jpg"
        ),},
    )


@session_admin_required
def admin_allusers_view(request):
    all_users = User.objects.all()
    data = {
        'all_users' : all_users,
    }
    return render(request, 'admin_panel/admin_allusers_page.html', data)






@session_admin_required
def admin_approvals_view(request):
    unapproved_users = User.objects.filter(is_approved = False)
    data = {
        'all_users' : unapproved_users
    }
    return render(request, 'admin_panel/admin_approvals_page.html',data)


@session_admin_required
def admin_faculty_view(request):
    faculty = User.objects.filter(user_type = 'faculty')
    data = {
        'all_users' : faculty
    }
    return render(request, 'admin_panel/admin_faculty_page.html',data)

@session_admin_required
def admin_alumni_view(request):
    alumni = User.objects.filter(user_type = 'alumni')
    data = {
        'all_users' : alumni
    }
    return render(request, 'admin_panel/admin_alumni_page.html',data)

@session_admin_required
def admin_students_view(request):
    students = User.objects.filter(user_type = 'students')
    data = {
        'all_users' : students
    }
    return render(request, 'admin_panel/admin_students_page.html',data)

@session_admin_required
def admin_settings_view(request):
    return render(request, 'admin_panel/admin_settings_page.html')
admin_settings_view



# ADMIN REMOVE and APPROVE Users
@session_admin_required
def approve_user_view(request, username):
    if request.method == "POST":
        
        user = get_object_or_404(User, username = username)
        if hasattr(user, "profile"):
            user.is_approved = True
            user.save()
            messages.success(request, f"{user.username} approved successfully!")
    return redirect("unicircleapp:admin_allusers_page")

@session_admin_required
def delete_user_view(request, username):
    if request.method == "POST":
        user = get_object_or_404(User, username = username)
        user.delete()
        messages.success(request, f"{user.username} deleted successfully!")
    return redirect("unicircleapp:admin_allusers_page")

def admin_view_posts(request):
    posts = Post.objects.all().order_by("-created_at")
    data = {
        'posts' : posts, 
    }
    return render(request,'admin_panel/admin_view_posts.html',data)




def view_fundraisers(request):
    return render(request,'fundraisers.html')


@login_required
def send_follow_request(request):
    if request.method == "POST":
        to_username = request.POST.get("to")
        followed = get_object_or_404(User, username=to_username)

        # Faculty cannot follow
        if request.user.user_type == 'faculty':
            return JsonResponse({"error": "Faculty cannot follow anyone"}, status=403)
        if followed == request.user:
            return JsonResponse({"error": "Cannot follow yourself"}, status=400)

        follow, created = Follow.objects.get_or_create(follower=request.user, followed=followed)
        if not created:
            return JsonResponse({"message": "Already requested"}, status=200)

        return JsonResponse({"message": "Follow request sent"}, status=201)

    return JsonResponse({"error": "Invalid request"}, status=400)


@login_required
def handle_follow_request(request):
    if request.method == "POST":
        follower_username = request.POST.get("from")
        action = request.POST.get("action")  # 'accept' or 'reject'
        follower = get_object_or_404(User, username=follower_username)

        follow = get_object_or_404(Follow, follower=follower, followed=request.user, status='pending')

        if action == "accept":
            follow.status = "accepted"
        elif action == "reject":
            follow.status = "rejected"
        else:
            return JsonResponse({"error": "Invalid action"}, status=400)

        follow.save()
        return JsonResponse({"message": f"Follow request {action}ed"})
    
    return JsonResponse({"error": "Invalid request"}, status=400)

def follow_status(request, username):
    target = get_object_or_404(User, username=username)
    if request.user.user_type == 'faculty':
        return JsonResponse({"status": "faculty_free"})

    follow = Follow.objects.filter(follower=request.user, followed=target).first()
    status = follow.status if follow else None
    return JsonResponse({"status": status})


@login_required
def fetch_follow_requests(request):
    # Only show requests where current user is followed and status is pending
    requests = Follow.objects.filter(followed=request.user, status='pending')
    data = [{
        "follower_username": f.follower.username,
        "follower_name": f.follower.get_full_name() or f.follower.username,
    } for f in requests]
    return JsonResponse({"requests": data})



@login_required
def my_followers(request):
    followers = Follow.objects.filter(followed=request.user, status='accepted')
    data = [
        {"username": f.follower.username, "full_name": f.follower.get_full_name() or f.follower.username}
        for f in followers
    ]
    return JsonResponse({"followers": data})

@login_required
def my_following(request):
    following = Follow.objects.filter(follower=request.user, status='accepted')
    data = [
        {"username": f.followed.username, "full_name": f.followed.get_full_name() or f.followed.username}
        for f in following
    ]
    return JsonResponse({"following": data})

@login_required
def remove_follower(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        f = Follow.objects.filter(follower__username=username, followed=request.user, status='accepted').first()
        if f:
            f.delete()
            return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)

@login_required
def unfollow_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        f = Follow.objects.filter(follower=request.user, followed__username=username, status='accepted').first()
        if f:
            f.delete()
            return JsonResponse({"success": True})
    return JsonResponse({"success": False}, status=400)




def validate_password_criteria(password):
    if not password:
        raise ValidationError("Password is required.")
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long.")
    if " " in password:
        raise ValidationError("Password must not contain spaces.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValidationError("Password must include at least one letter and one digit.")

def generate_valid_password():
    """Generates a random password until it passes validation."""
    while True:
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(chars) for _ in range(random.randint(10, 14)))
        try:
            validate_password_criteria(password)
            return password
        except ValidationError:
            continue

def forgot_password(request):
    if request.method == "POST":
        user_email = request.POST.get("email", "").strip()
        if not user_email:
            return JsonResponse({"error": "Email is required."}, status=400)

        try:
            user = get_object_or_404(User, email=user_email)
        except Exception:
            return JsonResponse({"error": "No user found with that email."}, status=404)

        # Generate a random secure password
        new_password = get_random_string(length=10)
        user.set_password(new_password)
        user.save()

        # Email details
        subject = "Reset Password - Unicircle"
        from_email = settings.EMAIL_HOST_USER
        to_email = [user_email]

        # Render HTML email content
        html_content = render_to_string(
            'email_template.html',
            {'username': user.username, 'password': new_password}
        )

        # Create email
        msg = EmailMultiAlternatives(
            subject=subject,
            body=f"Hello {user.username},\n\nYour new password is: {new_password}\nPlease change it after logging in.",
            from_email=from_email,
            to=to_email
        )
        msg.attach_alternative(html_content, "text/html")

        # Send the email
        msg.send(fail_silently=False)
        logout(request)
        return JsonResponse({"success": True, "message": "A new password has been sent to your email. You will be logged out"})

    return JsonResponse({"error": "Invalid request"}, status=400)