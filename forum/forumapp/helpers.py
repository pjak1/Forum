from typing import Any, Callable, Dict, List, Optional, Tuple
from django.apps import apps
from django.http import JsonResponse, HttpRequest
from django.utils import formats
from django.forms.models import model_to_dict
from django.db.models import F, Model, Count

ALLOWED_MODELS: List[str] = ['Reply', 'Category', 'Topic']
ALLOWED_FILTER_PARAMS: List[str] = ['topic__slug', 'category__slug', 'author_id']
ALLOWED_ANNOTATIONS: List[str] = ['author_name', 'replies']


def format_date_field(obj_dict: Dict[str, Any], obj: Model, date_field_name: str) -> None:
    """Formats a date field of an object into a human-readable format."""
    obj_dict[date_field_name] = formats.date_format(obj.created_at, format='DATETIME_FORMAT', use_l10n=True)


def add_annotated_fields_to_obj_attrs(obj_dict: Dict[str, Any], obj: Model, annotations: List[str]) -> None:
    """Adds annotated fields to the dictionary representation of an object."""
    for annotation in annotations:
        obj_dict[annotation] = getattr(obj, annotation)


def get_format_function(request: HttpRequest) -> Tuple[Optional[Callable], List[Any]]:
    """Retrieves the appropriate format function and its arguments from the request."""
    format_function_name: Optional[str] = request.GET.get('format_function')
    format_args: List[str] = request.GET.getlist('format_args[]', [])

    available_format_functions: Dict[str, Callable] = {
        'datetime_format': format_date_field,
    }

    return available_format_functions.get(format_function_name), format_args


def validate_filter_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validates the filter parameters and only allows safe parameters."""
    valid_params: Dict[str, Any] = {}
    for key, value in params.items():
        if key in ALLOWED_FILTER_PARAMS:
            valid_params[key] = value
    return valid_params


def validate_annotations(params: Dict[str, Any]) -> Dict[str, F]:
    """Validates annotations, ensuring only allowed annotations are used."""
    valid_annotations: Dict[str, F] = {}
    for key, value in params.items():
        if key.startswith('annotate_'):
            annotation_key = key[len('annotate_'):]
            if annotation_key in ALLOWED_ANNOTATIONS:
                valid_annotations[annotation_key] = F(value)
        elif key in ALLOWED_ANNOTATIONS:  # Check if it's a direct annotation (e.g., replies_count)
            valid_annotations[key] = F(value)
    return valid_annotations


def validate_related_counts(related_counts_request: str) -> List[str]:
    """Validates the related counts request, ensuring only allowed fields are used."""
    related_counts: List[str] = related_counts_request.split(',')
    valid_related_counts: List[str] = []

    for field in related_counts:
        if field in ALLOWED_ANNOTATIONS:
            valid_related_counts.append(field)
        else:
            raise ValueError(f"Invalid related count field: {field}")

    return valid_related_counts


def validate_model(model_name: str) -> Optional[JsonResponse]:
    if not model_name or model_name not in ALLOWED_MODELS:
        return JsonResponse({'error': 'Invalid or disallowed model'}, status=400)

    return None


def safe_model_to_dict(instance: Model, exclude_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """Safely converts a model instance to a dictionary, excluding sensitive fields."""
    exclude_fields = exclude_fields or []
    data: Dict[str, Any] = model_to_dict(instance)

    for field in exclude_fields:
        if field in data:
            del data[field]

    return data


def get_filter_params(request: HttpRequest) -> Dict[str, Any]:
    return {key: value for key, value in request.POST.items() if key not in ['page', 'per_page', 'model', 'related_counts', 'count']}


def validate_page_and_per_page(request: HttpRequest) -> Tuple[Optional[int], Optional[int]]:
    try:
        page: int = int(request.POST.get('page', 1))
        per_page: int = int(request.POST.get('per_page', 7))
        if page < 1 or per_page < 1:
            raise ValueError("Page and per_page must be positive integers.")
        return page, per_page
    except ValueError:
        return None, None


def get_model(model_name: str) -> Tuple[Optional[Model], Optional[JsonResponse]]:
    if not model_name or model_name not in ALLOWED_MODELS:
        return None, JsonResponse({'error': 'Invalid or disallowed model'}, status=400)

    try:
        model: Model = apps.get_model(app_label='forumapp', model_name=model_name)
        return model, None
    except LookupError:
        return None, JsonResponse({'error': f'Model {model_name} does not exist'}, status=400)


def fetch_objects(model: Model, filter_params: Dict[str, Any], annotations: Dict[str, F], related_counts_request: str, request: HttpRequest) -> Tuple[Optional[JsonResponse], Dict[str, F]]:
    try:
        objects = model.objects.filter(**filter_params)
        if annotations:
            objects = objects.annotate(**annotations)

        if related_counts_request:
            related_counts: List[str] = validate_related_counts(related_counts_request)
            related_counts_dict: Dict[str, Count] = {f'{field}_count': Count(field) for field in related_counts}
            annotations = {**annotations, **related_counts_dict}
            objects = objects.annotate(**related_counts_dict)

        if model.__name__ == 'Category' and not request.user.is_authenticated:
            objects = objects.exclude(slug='MyTopics')
        
        return objects, annotations
    except Exception as e:
        return JsonResponse({'error': f'Error filtering objects: {str(e)}'}, status=400)


def serialize_objects(page_objects: List[Model], annotations: Dict[str, F], related_counts_request: str, format_function: Optional[Callable], format_args: List[Any]) -> List[Dict[str, Any]]:
    objects_data: List[Dict[str, Any]] = []

    for obj in page_objects:
        obj_dict: Dict[str, Any] = safe_model_to_dict(obj, exclude_fields=['author_email', 'password'])

        if annotations or related_counts_request:
            add_annotated_fields_to_obj_attrs(obj_dict, obj, annotations)
        
        if format_function:
            format_function(obj_dict, obj, *format_args)

        objects_data.append(obj_dict)
    
    return objects_data


def create_response_data(objects_data: List[Dict[str, Any]], page_objects: List[Model], request: HttpRequest) -> Dict[str, Any]:
    response_data: Dict[str, Any] = {
        'objects': objects_data,
        'has_next': page_objects.has_next()
    }

    count_request: bool = request.POST.get('count', 'false').lower() == 'true'
    if count_request:
        response_data['count'] = len(objects_data)  # Count already fetched objects
    
    return response_data
