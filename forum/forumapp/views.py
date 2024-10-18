import json

from typing import Any, Callable, Dict, List, Optional, Tuple
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
from django.forms.models import model_to_dict
from django.db.models import F, Model, Count

from .models import Topic, Category, Reply
from .forms import SignUpForm, NewTopicForm

ALLOWED_MODELS = ['Reply', 'Category']
ALLOWED_FILTER_PARAMS = ['topic__slug']
ALLOWED_ANNOTATIONS = ['author_name', 'replies_count']


def format_date_field(obj_dict: Dict[str, Any], obj: Model, date_field_name: str) -> None:
    """
    Formats a date field of an object into a human-readable format.
    """
    obj_dict[date_field_name] = formats.date_format(obj.created_at, format='DATETIME_FORMAT', use_l10n=True)


def add_annotated_fields_to_obj_attrs(obj_dict: Dict[str, Any], obj: Model, annotations: List[str]) -> None:
    """
    Adds annotated fields to the dictionary representation of an object.
    """
    for annotation in annotations:
        obj_dict[annotation] = getattr(obj, annotation)


def get_format_function(request: HttpRequest) -> Tuple[Optional[Callable], List[Any]]:
    """
    Retrieves the appropriate format function and its arguments from the request.
    """
    format_function_name = request.GET.get('format_function')
    format_args = request.GET.getlist('format_args[]', [])

    available_format_functions = {
        'datetime_format': format_date_field,
    }

    return available_format_functions.get(format_function_name), format_args


def validate_filter_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates the filter parameters and only allows safe parameters.
    """
    valid_params = {}
    for key, value in params.items():
        if key in ALLOWED_FILTER_PARAMS:
            valid_params[key] = value
    return valid_params


def validate_annotations(params: Dict[str, Any]) -> Dict[str, F]:
    """
    Validates annotations, ensuring only allowed annotations are used.
    """
    valid_annotations = {}
    for key, value in params.items():
        if key.startswith('annotate_'):
            annotation_key = key[len('annotate_'):]
            if annotation_key in ALLOWED_ANNOTATIONS:
                valid_annotations[annotation_key] = F(value)
    return valid_annotations


def safe_model_to_dict(instance: Model, exclude_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Safely converts a model instance to a dictionary, excluding sensitive fields.
    """
    exclude_fields = exclude_fields or []
    data = model_to_dict(instance)

    for field in exclude_fields:
        if field in data:
            del data[field]

    return data


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
    page = int(request.POST.get('page', 1))
    per_page = int(request.POST.get('per_page', 7))
    model_name = request.POST.get('model')
    format_function, format_args = get_format_function(request)

    if not model_name or model_name not in ALLOWED_MODELS:
        return JsonResponse({'error': 'Invalid or disallowed model'}, status=400)

    try:
        model = apps.get_model(app_label='forumapp', model_name=model_name)
    except LookupError:
        return JsonResponse({'error': f'Model {model_name} does not exist'}, status=400)

    filter_params = {key: value for key, value in request.POST.items() if key not in ['page', 'per_page', 'model']}
    filter_params = validate_filter_params(filter_params)

    annotations = validate_annotations(request.GET)

    try:
        if annotations:
            objects = model.objects.filter(**filter_params).annotate(**annotations)
        else:
            objects = model.objects.filter(**filter_params)

        if model_name == 'Category' and not request.user.is_authenticated:
            objects = objects.exclude(slug='MyTopics')
    except Exception as e:
        return JsonResponse({'error': f'Error filtering objects: {str(e)}'}, status=400)

    paginator = Paginator(objects, per_page)
    page_objects = paginator.get_page(page)

    objects_data = []

    for obj in page_objects:
        obj_dict = safe_model_to_dict(obj, exclude_fields=['author_email', 'password'])

        if annotations:
            add_annotated_fields_to_obj_attrs(obj_dict, obj, annotations)

        if format_function:
            format_function(obj_dict, obj, *format_args)

        objects_data.append(obj_dict)

    return JsonResponse({
        'objects': objects_data,
        'has_next': page_objects.has_next()
    })


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

    if category.name == 'My Topics':
        topics = Topic.objects.filter(author=request.user)
    else:
        topics = category.topics.all()

    return render(request, 'category_detail.html', {'category': category, 'topics': topics, 'categories': categories})


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
