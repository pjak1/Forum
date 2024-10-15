from django.urls import path
from django.views.i18n import JavaScriptCatalog
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path('topic/<slug:slug>/', views.topic_detail, name='topic_detail'),
    path('category/', views.category_list, name='category_list'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('new-topic/', views.new_topic, name='new_topic'),
    path('sign-up/', views.sign_up, name='sign_up'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('new-reply/', views.new_reply, name='new_reply'),
    path('load-objects/', views.load_objects, name='load_objects'),
]
