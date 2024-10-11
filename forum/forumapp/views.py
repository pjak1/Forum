from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext
from .models import Topic, Category
from .forms import SignUpForm


def index(request):
    topics = Topic.objects.all()
    return render(request, 'index.html', {'topics': topics})


def new_topic(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        # Handle topic creation form submission here
        pass
    categories = Category.objects.all()
    return render(request, 'new_topic.html', {'categories': categories})


def topic_detail(request, id):
    topic = get_object_or_404(Topic, id=id)
    return render(request, 'topic_detail.html', {'topic': topic})


def category_detail(request, id):
    category = get_object_or_404(Category, id=id)
    categories = Category.objects.all()
    topics = category.topics.all()  # Get all topics associated with the category
    return render(request, 'category_detail.html', {'category': category, 'topics': topics, 'categories': categories})


def category_list(request):
    categories = Category.objects.all()
    return render(request, 'category_list.html', {'categories': categories})


def sign_up(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()  # Save the new user
            return redirect('index')  # Redirect to the home page after successful registration
    else:
        form = SignUpForm()
    return render(request, 'sign_up.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')  # Redirect to a homepage after successful login
            else:
                messages.error(request, gettext("Invalid username or password."))  # Add error message
        else:
            messages.error(request, gettext("Invalid username or password."))  # Add error message for invalid form

    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('index')