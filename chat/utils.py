# chat/utils.py or wherever your helper lives
from unicircleapp.models import Follow

def can_message(sender, receiver):
    sender_type = getattr(sender, "user_type", None)
    receiver_type = getattr(receiver, "user_type", None)

    # Faculty can message anyone
    if sender_type == "faculty":
        return True

    # Alumni rules
    if sender_type == "alumni":
        if receiver_type in ["student", "alumni"]:
            return True
        elif receiver_type == "faculty":
            follow = Follow.objects.filter(follower=sender, followed=receiver, status='accepted').exists()
            return follow
        return False

    # Student rules
    if sender_type == "student":
        if receiver_type == "student":
            return True
        else:  # Alumni or Faculty
            follow = Follow.objects.filter(follower=sender, followed=receiver, status='accepted').exists()
            return follow

    # Default fallback
    return False
