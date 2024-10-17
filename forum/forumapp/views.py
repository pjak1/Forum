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

ALLOWED_MODELS = ['Reply']

def format_date_field(obj_dict, obj, date_field_name):
    obj_dict[date_field_name] = formats.date_format(obj.created_at, format='DATETIME_FORMAT', use_l10n=True)

def add_anotated_fields_to_obj_attrs(obj_dict, obj, annotations):
    for annotation in annotations:
        obj_dict[annotation] = getattr(obj, annotation)

def get_format_function(request):
    """
    Získá formátovací funkci a její argumenty z požadavku.
    """
    format_function_name = request.GET.get('format_function')
    format_args = request.GET.getlist('format_args[]', [])

    available_format_functions = {
        'datetime_format': format_date_field,
        # Přidej další funkce podle potřeby
    }

    return available_format_functions.get(format_function_name), format_args

def index(request):
    topics = Topic.objects.all()
    return render(request, 'index.html', {'topics': topics})

@login_required
def new_topic(request):
    if request.method == 'POST':
        category_id = request.POST.get('category')  # Get category ID from POST
        category = get_object_or_404(Category, id=category_id)  # Find the category by ID
        form = NewTopicForm(request.POST)

        if category.name != 'MyTopics':  # Verify that it is not 'MyTopics'
            if form.is_valid():
                topic = form.save(commit=False)  # commit=False to not save immediately
                topic.category = category  # Set the category correctly
                topic.author = request.user
                topic.save()
                return redirect('category_detail', slug=category.slug)
            else:
                # If the form is invalid, show the form again
                categories = Category.objects.all()
                return render(request, 'new_topic.html', {'categories': categories, 'form': form})
        else:
            # Handle the invalid category 'MyTopics'
            categories = Category.objects.all()
            return render(request, 'new_topic.html', {'categories': categories, 'form': form, 'error': 'Invalid category selected'})
    else:
        categories = Category.objects.all()
        form = NewTopicForm()
        return render(request, 'new_topic.html', {'categories': categories, 'form': form})

@require_POST
def load_objects(request): # TODO: ošetřit nebezpečné vstupy v url a případně optimalizace funkce
    """
    Načítá objekty podle požadavku klienta s možností filtrování, stránkování a volitelné anotace.
    """
    page = int(request.POST.get('page', 1))
    per_page = int(request.POST.get('per_page', 7))
    model_name = request.POST.get('model')
    format_function, format_args = get_format_function(request)

    # Ověření modelu
    if not model_name or model_name not in ALLOWED_MODELS:
        return JsonResponse({'error': 'Invalid or disallowed model'}, status=400)

    try:
        model = apps.get_model(app_label='forumapp', model_name=model_name)
    except LookupError:
        return JsonResponse({'error': f'Model {model_name} does not exist'}, status=400)

    # Dynamické filtrování založené na parametrech POST požadavku
    filter_params = {key: value for key, value in request.POST.items() if key not in ['page', 'per_page', 'model']}
    
    # Získání anotací z query parametrů
    annotations = {}
    for key, value in request.GET.items():
        if key.startswith('annotate_'):
            annotation_key = key[len('annotate_'):]  # Odebrání prefixu 'annotate_'
            annotations[annotation_key] = F(value)   # Přidání anotace jako F() objekt

    try:
        # Pouze pokud existují anotace, přidáme je do dotazu
        if annotations:
            objects = model.objects.filter(**filter_params).annotate(**annotations)
        else:
            objects = model.objects.filter(**filter_params)

    except Exception as e:
        return JsonResponse({'error': f'Error filtering objects: {str(e)}'}, status=400)

    # Stránkování
    paginator = Paginator(objects, per_page)
    page_objects = paginator.get_page(page)

    objects_data = []

    for obj in page_objects:
        obj_dict = model_to_dict(obj)

        # Přidání anotovaných polí
        if annotations:
            add_anotated_fields_to_obj_attrs(obj_dict, obj, annotations)

        # Zavolej formátovací funkci, pokud byla vybrána
        if format_function:
            format_function(obj_dict, obj, *format_args)  # Předání argumentů z klienta do funkce

        objects_data.append(obj_dict)

    return JsonResponse({
        'objects': objects_data,
        'has_next': page_objects.has_next()
    })

def topic_detail(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    return render(request, 'topic_detail.html', {'topic': topic})

@login_required
@require_POST
def new_reply(request):
    try:
        # Load the JSON data from the request body
        data = json.loads(request.body)
        reply_text = data.get('reply')

        # Retrieve topic slug
        topic_slug = data.get('topic_slug')

        author = request.user

        # Fetch the related Topic instance
        topic = Topic.objects.get(slug=topic_slug)

        # Create and save the new reply
        reply = Reply(content=reply_text, topic=topic, author=author)
        reply.save()
        formatted_time = formats.date_format(reply.created_at, "DATETIME_FORMAT")

        return JsonResponse({'status': 'success', 'time': formatted_time})
    except Topic.DoesNotExist as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

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
                return redirect('index')  # Redirect to the homepage after successful login
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
