from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()

def message_file_path(instance, filename):
    # chat_files/user_<id>/<filename>
    return f'chat_files/user_{instance.sender.id}/{filename}'

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_messages")
    text = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    file = models.FileField(upload_to=message_file_path, blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(default=0)

    class Meta:
        ordering = ["timestamp"]

    def get_file_size_display(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"


class GroupMessage(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_messages")
    text = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    file = models.FileField(upload_to='chat_files/group/', blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.IntegerField(default=0)

    class Meta:
        ordering = ["timestamp"]
    
    def get_file_size_display(self):
        """Форматированный размер файла"""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"