from django.contrib import admin
from .models import Category, Topic, Reply

admin.site.register(Topic)
admin.site.register(Category)
admin.site.register(Reply)