from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext
from .models import Topic, Category
from .forms import SignUpForm, NewTopicForm


def index(request):
    topics = Topic.objects.all()
    return render(request, 'index.html', {'topics': topics})


@login_required
def new_topic(request):
    if request.method == 'POST':
        category_id = request.POST.get('category')  # Získání id kategorie z POST
        category = get_object_or_404(Category, id=category_id)  # Najdi kategorii podle id
        form = NewTopicForm(request.POST)

        if category.name != 'MyTopics':  # Ověř, že to není 'MyTopics'
            if form.is_valid():
                topic = form.save(commit=False)  # commit=False to not save immediately
                topic.category = category  # Nastav kategorii správně
                topic.author = request.user
                topic.save()
                return redirect('category_detail', slug=category.slug)
            else:
                # Pokud je formulář neplatný, zobraz formulář znovu
                categories = Category.objects.all()
                return render(request, 'new_topic.html', {'categories': categories, 'form': form})
        else:
            # Ošetři neplatnou kategorii 'MyTopics'
            categories = Category.objects.all()
            return render(request, 'new_topic.html', {'categories': categories, 'form': form, 'error': 'Invalid category selected'})
    else:
        categories = Category.objects.all()
        form = NewTopicForm()
        return render(request, 'new_topic.html', {'categories': categories, 'form': form})



def topic_detail(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    return render(request, 'topic_detail.html', {'topic': topic})


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    categories = Category.objects.all()

    if category.name == 'My Topics':
        # Show only topics created by the logged-in user
        topics = Topic.objects.filter(author=request.user)
    else:
        # Show all topics for the category
        topics = category.topics.all()
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
                messages.error(request, gettext("Invalid username or password."))
        else:
            messages.error(request, gettext("Invalid username or password."))

    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


def user_logout(request):
    logout(request)
    return redirect('index')
