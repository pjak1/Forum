from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('topic/<int:id>/', views.topic_detail, name='topic_detail'),
    path('category/', views.category_list, name='category_list'),
    path('category/<int:id>/', views.category_detail, name='category_detail'),
    path('new-topic/<int:category_id>/', views.new_topic, name='new_topic'),
    path('sign-up/', views.sign_up, name='sign_up'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
]