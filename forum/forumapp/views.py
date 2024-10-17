import json

from django.http import JsonResponse
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
from django.db.models import F
from .models import Topic, Category, Reply
from .forms import SignUpForm, NewTopicForm

# Allowed models for dynamic object loading
ALLOWED_MODELS = ['Reply', 'Category']

# Allowed filter parameters to prevent unsafe or unnecessary filtering
ALLOWED_FILTER_PARAMS = ['topic', 'author', 'created_at']

# Allowed annotations for dynamic fields
ALLOWED_ANNOTATIONS = ['author_name']

# Function to format date fields in the dictionary representing an object
def format_date_field(obj_dict, obj, date_field_name):
    obj_dict[date_field_name] = formats.date_format(obj.created_at, format='DATETIME_FORMAT', use_l10n=True)

# Function to add annotated fields to the object's dictionary
def add_anotated_fields_to_obj_attrs(obj_dict, obj, annotations):
    for annotation in annotations:
        obj_dict[annotation] = getattr(obj, annotation)

# Function to retrieve the appropriate format function and its arguments from the request
def get_format_function(request):
    format_function_name = request.GET.get('format_function')
    format_args = request.GET.getlist('format_args[]', [])

    available_format_functions = {
        'datetime_format': format_date_field,
    }

    return available_format_functions.get(format_function_name), format_args

# Function to validate the filter parameters and only allow safe parameters
def validate_filter_params(params):
    valid_params = {}
    for key, value in params.items():
        if key in ALLOWED_FILTER_PARAMS:
            valid_params[key] = value
    return valid_params

# Function to validate annotations, ensuring only allowed annotations are used
def validate_annotations(params):
    valid_annotations = {}
    for key, value in params.items():
        if key.startswith('annotate_'):
            annotation_key = key[len('annotate_'):]
            if annotation_key in ALLOWED_ANNOTATIONS:
                valid_annotations[annotation_key] = F(value)
    return valid_annotations

# Function to safely convert model instances to dictionaries, excluding sensitive fields
def safe_model_to_dict(instance, exclude_fields=None):
    exclude_fields = exclude_fields or []
    data = model_to_dict(instance)

    # Remove sensitive fields from the data
    for field in exclude_fields:
        if field in data:
            del data[field]
    
    return data

# View to render the index page with a list of topics
def index(request):
    topics = Topic.objects.order_by('-created_at')[:10]  # Získá prvních 10 nejnovějších topics
    return render(request, 'index.html', {'topics': topics})

# View to create a new topic, requiring user login
@login_required
def new_topic(request):
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

# View to load objects dynamically, supporting filtering, pagination, and annotations
@require_POST
def load_objects(request):
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

    # Validate and filter the request parameters
    filter_params = {key: value for key, value in request.POST.items() if key not in ['page', 'per_page', 'model']}
    filter_params = validate_filter_params(filter_params)

    # Validate annotations from GET parameters
    annotations = validate_annotations(request.GET)

    try:
        if annotations:
            objects = model.objects.filter(**filter_params).annotate(**annotations)
        else:
            objects = model.objects.filter(**filter_params)
    except Exception as e:
        return JsonResponse({'error': f'Error filtering objects: {str(e)}'}, status=400)

    paginator = Paginator(objects, per_page)
    page_objects = paginator.get_page(page)

    objects_data = []
    
    for obj in page_objects:
        # Safely convert object to a dictionary, excluding sensitive fields
        obj_dict = safe_model_to_dict(obj, exclude_fields=['author_email', 'password'])

        # Add annotated fields to the object dictionary
        if annotations:
            add_anotated_fields_to_obj_attrs(obj_dict, obj, annotations)

        # Apply formatting if a format function is provided
        if format_function:
            format_function(obj_dict, obj, *format_args)

        objects_data.append(obj_dict)

    return JsonResponse({
        'objects': objects_data,
        'has_next': page_objects.has_next()
    })

# View to create a new reply to a topic, requiring user login
@login_required
@require_POST
def new_reply(request):
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
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500) #TODO: categorie dynamické načítání

# View to display a topic detail page
def topic_detail(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    return render(request, 'topic_detail.html', {'topic': topic})

# View to display topics within a specific category
def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    categories = Category.objects.all()

    # Show only the logged-in user's topics if the category is "My Topics"
    if category.name == 'My Topics':
        topics = Topic.objects.filter(author=request.user)
    else:
        topics = category.topics.all()

    return render(request, 'category_detail.html', {'category': category, 'topics': topics, 'categories': categories})

# View to display the list of all categories
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'category_list.html', {'categories': categories})

# View to handle user sign-up
def sign_up(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = SignUpForm()
    return render(request, 'sign_up.html', {'form': form})

# View to handle user login
def user_login(request):
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

# View to handle user logout
def user_logout(request):
    logout(request)
    return redirect('index')
