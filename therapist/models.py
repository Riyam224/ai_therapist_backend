from django.db import models


class MoodEntry(models.Model):
    user_id = models.CharField(max_length=128, db_index=True)
    emoji = models.CharField(max_length=10)  # Store emoji
    thoughts = models.TextField()  # Store user thoughts
    ai_response = models.TextField()  # Store AI response
    created_at = models.DateTimeField(auto_now_add=True)  # Entry timestamp

    def __str__(self):
        return f"{self.user_id} | {self.emoji} - {self.thoughts[:20]}"

    class Meta:
        verbose_name = "MoodEntry"
        verbose_name_plural = "MoodEntries"
