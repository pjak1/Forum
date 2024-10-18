from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from datetime import datetime


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Topic(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='topics')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='topics')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super(Topic, self).save(*args, **kwargs)

    def __str__(self):
        return self.title


class Reply(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField()
    # Automatically update the timestamp on edits
    updated_at = models.DateTimeField(auto_now=True)
    # Support threaded replies
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    slug = models.SlugField(unique=True, blank=True)

    def __str__(self):
        return f'Reply by {self.author} on {self.topic.title}'
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.created_at = datetime.now()
            timestamp = int(self.created_at.timestamp())
            self.slug = slugify(f"{self.topic.id}-{self.author.id}-{timestamp}")
        super().save(*args, **kwargs)