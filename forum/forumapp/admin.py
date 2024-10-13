from django.contrib import admin
from .models import Category, Topic, Reply
# Register your models here.
admin.site.register(Topic)
admin.site.register(Category)
admin.site.register(Reply)