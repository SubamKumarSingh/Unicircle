import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from .models import Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_authenticated:
            self.user = self.scope["user"]
            # Each user has a group to receive messages
            await self.channel_layer.group_add(f"user_{self.user.username}", self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, "user"):
            await self.channel_layer.group_discard(f"user_{self.user.username}", self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        command = data.get("command")

        if command == "switch_chat":
            other_username = data["with"]
            try:
                other_user = await sync_to_async(User.objects.get)(username=other_username)
            except User.DoesNotExist:
                await self.send(text_data=json.dumps({"error": "User not found"}))
                return

            messages = await sync_to_async(list)(Message.objects.filter(
                sender__in=[self.user, other_user],
                receiver__in=[self.user, other_user]
            ).order_by("-timestamp")[:50])

            messages_data = [
                {
                    "sender": msg.sender.username,
                    "sender_pic": msg.sender.profile.picture.url if hasattr(msg.sender, "profile") else "",
                    "content": msg.content,
                    "mine": msg.sender_id == self.user.id
                }
                for msg in messages
            ]

            await self.send(text_data=json.dumps({
                "command": "chat_history",
                "messages": messages_data,
                "other_user": {
                    "username": other_user.username,
                    "name": other_user.get_full_name(),
                    "picture": other_user.profile.picture.url if hasattr(other_user, "profile") else ""
                }
            }))

        elif command == "new_message":
            receiver_username = data["to"]
            message_text = data["message"]
            receiver = await sync_to_async(User.objects.get)(username=receiver_username)

            msg = await sync_to_async(Message.objects.create)(
                sender=self.user,
                receiver=receiver,
                content=message_text
            )

            event = {
                "command": "new_message",
                "sender": msg.sender.username,
                "sender_pic": msg.sender.profile.picture.url if hasattr(msg.sender, "profile") else "",
                "content": msg.content,
                "to": receiver.username,
            }

            # send to both users
            await self.channel_layer.group_send(
                f"user_{receiver.username}", {"type": "chat.message", "event": event}
            )
            await self.channel_layer.group_send(
                f"user_{self.user.username}", {"type": "chat.message", "event": event}
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["event"]))
