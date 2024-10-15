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

def format_date_field(objects_data, obj):
    obj_dict = model_to_dict(obj)

    if 'created_at' in obj_dict:
        obj_dict['created_at'] = formats.date_format(obj.created_at, format='DATETIME_FORMAT', use_l10n=True)  # Naformátování data
    objects_data.append(obj_dict)

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


@require_POST
def load_objects(request):
    page = int(request.POST.get('page', 1))  
    per_page = int(request.POST.get('per_page', 7))  
    model_name = request.POST.get('model')
    format_function = request.GET.get('format_function')  # Získání jména funkce z query parameter

    available_format_functions = {
        'datetime_format': format_date_field,
        # Přidejte další funkce podle potřeby
    }

    if not model_name or model_name not in ALLOWED_MODELS:
        return JsonResponse({'error': 'Invalid or disallowed model'}, status=400)

    try:
        # Dynamicky načteme model jen pokud je v povolených modelech
        model = apps.get_model(app_label='forumapp', model_name=model_name)
    except LookupError:
        return JsonResponse({'error': f'Model {model_name} does not exist'}, status=400) # TODO: Change error message to be less specific

    # Filtrovat dynamicky na základě parametrů POST požadavku
    filter_params = {key: value for key, value in request.POST.items() if key not in ['page', 'per_page', 'model']}
    
    try:
        objects = model.objects.filter(**filter_params).annotate(author_name=F('author__username'))  # TODO: Zprovoznit annotate
    except Exception as e:
        return JsonResponse({'error': f'Error filtering objects: {str(e)}'}, status=400)

    paginator = Paginator(objects, per_page)
    page_objects = paginator.get_page(page)
    format_fields = available_format_functions.get(format_function) if format_function else None
    objects_data = []

    for obj in page_objects:
        format_fields(objects_data, obj)

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

        author= request.user

        # Fetch the related Topic instance
        topic = Topic.objects.get(slug=topic_slug)

        # Create and save the new reply
        reply = Reply(content=reply_text, topic=topic, 
                                    author=author)
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
