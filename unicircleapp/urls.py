from django.urls import path,include
from . import views

app_name = "unicircleapp"


urlpatterns = [
    path('',views.landing,name='landingpage'),

    # NAVBAR LINKS 
    path('dashboard/',views.dashboard,name='dashboardpage'),
    path('newProfile/',views.profileCreation,name='profileCreationpage'),
    path('logout/',views.logoutUser,name='logoutpage'),
    path("search/", views.search_results, name="search_results"),
    path("live-search/", views.live_search, name="live_search"),
    path("delete_account/", views.delete_account, name="delete_account"),
    # path("change_password/", views.change_password, name="change_password"),
    path("change-password/", views.change_password_view, name="change_password"),
    

    # FOLLOW URLS
    # send_follow_request
    path("send_follow_request/", views.send_follow_request, name="send_follow_request"),
    path("handle_follow_request/", views.handle_follow_request, name="handle_follow_request"),
    path("fetch_follow_requests/", views.fetch_follow_requests, name="fetch_follow_requests"),
    path('my_followers/', views.my_followers, name='my_followers'),
    path('my_following/', views.my_following, name='my_following'),
    path('remove_follower/', views.remove_follower, name='remove_follower'),
    path('unfollow_user/', views.unfollow_user, name='unfollow_user'),
    path("forgot_password/", views.forgot_password, name="forgot_password"),

    # GOOGLE SIGN UP 
    path("signup/then-google/", views.local_signup_then_google, name="local_signup_then_google"),
    path('accounts/google/mylogin/', views.google_direct, name='google_direct'),

    # ADMIN SIDEBAR ROUTES
    path('admin-panel/',views.admin_dashboard,name='admin_dashboard_page'),
    path('admin-allusers-list/',views.admin_allusers_view,name='admin_allusers_page'),
    path('admin-pending-approvals/',views.admin_approvals_view,name='admin_approvals_page'),
    path('admin-faculty-list/',views.admin_faculty_view,name='admin_faculty_page'),
    path('admin-alumni-list/',views.admin_alumni_view,name='admin_alumni_page'),
    path('admin-students-list/',views.admin_students_view,name='admin_students_page'),
    path('admin-settings/',views.admin_settings_view,name='admin_settings_page'),
    path('admin-view-posts/',views.admin_view_posts,name='admin_view_posts_page'),


    # ADMIN CLICK ROUTES
     path("admin_users_view/<str:username>/", views.admin_user_profile_view, name="admin_user_profile_page"),
     path("admin_approve_user/<str:username>/", views.approve_user_view, name="approve_user_page"),
     path("admin_delete_user/<str:username>/", views.delete_user_view, name="delete_user_page"),
    
    # TEMP ROUTE FOR FUNDRAISERS
    path("fundraisers/",views.view_fundraisers,name = "view_fundraisers_page"),
    # PROFILE BASED ROUTES
    path("editprofile/",views.user_edit_profile,name = "user_edit_profile_page"),
    path("<str:uname>/",views.user_view_profile,name = "user_view_profile_page"),






]