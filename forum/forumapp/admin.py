from django.contrib import admin
from .models import Category, Topic
# Register your models here.
admin.site.register(Topic)
admin.site.register(Category)