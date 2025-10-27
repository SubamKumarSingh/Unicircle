# chats/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from chat.utils import can_message

from .models import Message
from django.db import models

User = get_user_model()

@login_required
def chat_page(request):
    from unicircleapp.models import Follow

    # All users except self
    other_users = User.objects.exclude(id=request.user.id)

    users_data = []

    for u in other_users:
        # unread messages sent by u to current user
        unread_count = Message.objects.filter(
            sender=u, receiver=request.user, is_seen=False
        ).count()

        # last message between the two (could be from either side)
        last_msg = Message.objects.filter(
            sender__in=[request.user, u],
            receiver__in=[request.user, u]
        ).order_by('-timestamp').first()

        if last_msg:
            last_time = last_msg.timestamp
            preview = last_msg.content[:50]  # small preview
            from_me = (last_msg.sender_id == request.user.id)
        else:
            last_time = None
            preview = ""
            from_me = False

        # Profile picture handling
        profile = getattr(u, "profile", None)
        picture = (
            profile.profile_picture.url
            if profile and getattr(profile, "profile_picture", None)
            else ""
        )

        # Default values
        follow_status = None
        follow_allowed = False

        # Determine follow permission and status based on role hierarchy
        user_type = getattr(request.user, "user_type", None)
        other_type = getattr(u, "user_type", None)

        if user_type == "faculty":
            # Faculty can chat with anyone, no follow required
            follow_status = "faculty_free"
            follow_allowed = False

        elif user_type == "alumni":
            if other_type == "faculty":
                # Alumni -> Faculty needs follow
                follow_allowed = True
                f = Follow.objects.filter(follower=request.user, followed=u).first()
                follow_status = f.status if f else None
            else:
                # Alumni -> Student or Alumni = free chat
                follow_status = "free"
                follow_allowed = False

        elif user_type == "student":
            if other_type == "student":
                # Student -> Student = free chat
                follow_status = "free"
                follow_allowed = False
            else:
                # Student -> Alumni or Faculty needs follow
                follow_allowed = True
                f = Follow.objects.filter(follower=request.user, followed=u).first()
                follow_status = f.status if f else None

        else:
            # Default fallback (if user_type missing)
            follow_status = None
            follow_allowed = False
        follow_status = Follow.objects.filter(follower=request.user, followed=u).first()

        users_data.append({
            "username": u.username,
            "full_name": u.get_full_name() or u.username,
            "picture": picture,
            "unread_count": unread_count,
            "last_time": last_time,
            "last_preview": preview,
            "last_from_me": from_me,
            "follow_allowed": follow_allowed,   # True if Follow button should appear
            "follow_status": follow_status,     # 'pending', 'accepted', 'free', etc.
            "user_type": other_type,            # helpful for UI
        })

    return render(request, "chat.html", {"users_data": users_data})


def fetch_messages(request, username):
    try:
        other_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    # Mark unread messages from other_user to request.user as seen, since user opened the chat
    Message.objects.filter(sender=other_user, receiver=request.user, is_seen=False).update(is_seen=True,)

    messages = Message.objects.filter(
        sender__in=[request.user, other_user],
        receiver__in=[request.user, other_user]
    ).order_by('timestamp')

    def get_pic(user):
        profile = getattr(user, "profile", None)
        if profile and getattr(profile, "profile_picture", None):
            return profile.profile_picture.url
        return ""  # default blank if no picture

    data = [
        {
            "sender": msg.sender.username,
            "sender_pic": get_pic(msg.sender),
            "content": msg.content,
            "mine": msg.sender_id == request.user.id,
            "timestamp": msg.timestamp.isoformat()
        }
        for msg in messages
    ]

    return JsonResponse({
        "messages": data,
        "other_user": {
            "username": other_user.username,
            "name": other_user.get_full_name(),
            "picture": get_pic(other_user)
        }
    })


def send_message(request):
    if request.method == "POST":
        to_username = request.POST.get("to")
        content = request.POST.get("message")
        if not to_username or not content:
            return JsonResponse({"error": "Missing data"}, status=400)
        try:
            receiver = User.objects.get(username=to_username)
        except User.DoesNotExist:
            return JsonResponse({"error": "Receiver not found"}, status=404)
        if not can_message(request.user, receiver):
            return JsonResponse(
                {"error": "You cannot message this user until they accept your follow request."},
                status=403
            )
        msg = Message.objects.create(sender=request.user, receiver=receiver, content=content)
        profile = getattr(msg.sender, "profile", None)
        sender_pic = profile.profile_picture.url if profile and getattr(profile, "profile_picture", None) else ""

        return JsonResponse({
            "sender": msg.sender.username,
            "sender_pic": sender_pic,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat()
        })

    return JsonResponse({"error": "Invalid request"}, status=400)



def unread_summary(request):
    """
    returns:
      - total_unread_senders: how many distinct users have at least 1 unread message for current user
      - per_user: list of {username, unread_count}
    Useful for navbar badge + updating left-hand list without reloading the page.
    """
    # distinct users who sent unread messages to the current user
    qs = Message.objects.filter(receiver=request.user, is_seen=False).values('sender').distinct()
    total_unread_senders = qs.count()

    # per-user counts
    per = Message.objects.filter(receiver=request.user, is_seen=False).values('sender__username').annotate(count=models.Count('id')).order_by()
    per_list = [{"username": p['sender__username'], "unread_count": p['count']} for p in per]

    return JsonResponse({
        "total_unread_senders": total_unread_senders,
        "per_user": per_list
    })