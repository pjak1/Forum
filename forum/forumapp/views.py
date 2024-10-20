import json

from django.http import JsonResponse, HttpRequest, HttpResponse
from django.apps import apps
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import formats
from django.utils.translation import gettext

from .models import Topic, Category, Reply
from .forms import SignUpForm, NewTopicForm
from .helpers import (
    get_format_function,
    validate_filter_params,
    validate_annotations,
    get_filter_params,
    validate_page_and_per_page,
    get_model,
    fetch_objects,
    serialize_objects,
    create_response_data
)

ALLOWED_MODELS = ['Reply', 'Category', 'Topic']
ALLOWED_FILTER_PARAMS = ['topic__slug', 'category__slug', 'author_id']
ALLOWED_ANNOTATIONS = ['author_name', 'replies']

def index(request: HttpRequest) -> HttpResponse:
    """
    Renders the index page with a list of topics.
    """
    topics = Topic.objects.order_by('-created_at')[:10]
    return render(request, 'index.html', {'topics': topics})


@login_required
def new_topic(request: HttpRequest) -> HttpResponse:
    """
    Handles the creation of a new topic. Requires user login.
    """
    if request.method == 'POST':
        category_id = request.POST.get('category')
        category = get_object_or_404(Category, id=category_id)
        form = NewTopicForm(request.POST)

        if category.name != 'MyTopics':
            if form.is_valid():
                topic = form.save(commit=False)
                topic.category = category
                topic.author = request.user
                topic.save()
                return redirect('category_detail', slug=category.slug)
            else:
                categories = Category.objects.all()
                return render(request, 'new_topic.html', {'categories': categories, 'form': form})
        else:
            categories = Category.objects.all()
            return render(request, 'new_topic.html', {'categories': categories, 'form': form, 'error': 'Invalid category selected'})
    else:
        categories = Category.objects.all()
        form = NewTopicForm()
        return render(request, 'new_topic.html', {'categories': categories, 'form': form})

@require_POST
def load_objects(request: HttpRequest) -> JsonResponse:
    """
    Dynamically loads objects, supporting filtering, pagination, and annotations.
    """
    page, per_page = validate_page_and_per_page(request)
    if page is None or per_page is None:
        return JsonResponse({'error': 'Invalid page or per_page'}, status=400)

    model_name = request.POST.get('model')
    format_function, format_args = get_format_function(request)

    model, error_response = get_model(model_name)
    if error_response:
        return error_response

    filter_params = get_filter_params(request)
    filter_params = validate_filter_params(filter_params)

    annotations = validate_annotations(request.GET)
    related_counts_request = request.GET.get('related_counts', '')

    objects, annotations = fetch_objects(model, filter_params, annotations, related_counts_request, request)
    if isinstance(objects, JsonResponse):
        return objects

    paginator = Paginator(objects, per_page)
    page_objects = paginator.get_page(page)

    objects_data = serialize_objects(page_objects, annotations, related_counts_request, format_function, format_args)

    response_data = create_response_data(objects_data, page_objects, request)

    return JsonResponse(response_data)


@login_required
@require_POST
def new_reply(request: HttpRequest) -> JsonResponse:
    """
    Creates a new reply to a topic. Requires user login.
    """
    try:
        data = json.loads(request.body)
        reply_text = data.get('reply')
        topic_slug = data.get('topic_slug')

        author = request.user
        topic = Topic.objects.get(slug=topic_slug)

        reply = Reply(content=reply_text, topic=topic, author=author)
        reply.save()
        formatted_time = formats.date_format(reply.created_at, "DATETIME_FORMAT")

        return JsonResponse({'status': 'success', 'time': formatted_time})
    except Topic.DoesNotExist as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def topic_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Displays a topic detail page.
    """
    topic = get_object_or_404(Topic, slug=slug)
    return render(request, 'topic_detail.html', {'topic': topic, 'is_topic_detail': True})


def category_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Displays topics within a specific category.
    """
    category = get_object_or_404(Category, slug=slug)
    categories = Category.objects.all()

    user_id = ''

    if category.name == 'My Topics':
        user_id = request.user.id


    return render(request, 'category_detail.html', {'category': category, 'user_id': user_id, 'categories': categories, 'is_category_detail': True})


def category_list(request: HttpRequest) -> HttpResponse:
    """
    Displays the list of all categories.
    """
    categories = Category.objects.all()
    return render(request, 'category_list.html', {'categories': categories, 'is_category_list': True})


def sign_up(request: HttpRequest) -> HttpResponse:
    """
    Handles user sign-up.
    """
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = SignUpForm()
    return render(request, 'sign_up.html', {'form': form})


def user_login(request: HttpRequest) -> HttpResponse:
    """
    Handles user login.
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')
            else:
                messages.error(request, gettext("Invalid username or password."))
        else:
            messages.error(request, gettext("Invalid username or password."))

    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})


def user_logout(request: HttpRequest) -> HttpResponse:
    """
    Handles user logout.
    """
    logout(request)
    return redirect('index')
