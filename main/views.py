from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import (
    Property,
    PropertyPhoto,
    Unit,
    OwnerProfile,
    OwnerDocument,
    Application,
    BackgroundCheckRequest,
)

# TEMPORARY HOMEPAGE
def temp_home(request):
    return render(request, "home_temp.html")


def property_list(request):
    properties = Property.objects.all().select_related('owner').prefetch_related('photos')
    return render(request, 'main/property_list.html', {'properties': properties})


def property_detail(request, slug):
    property_obj = get_object_or_404(
        Property.objects.prefetch_related('photos', 'units', 'owner__documents'),
        slug=slug
    )
    photos = property_obj.photos.all()
    units = property_obj.units.filter(is_available=True)
    owner_documents_public = property_obj.owner.documents.filter(show_to_public=True)
    return render(request, 'main/property_detail.html', {
        'property': property_obj,
        'photos': photos,
        'units': units,
        'owner_documents_public': owner_documents_public,
    })


def apply_for_property(request, slug):
    property_obj = get_object_or_404(Property, slug=slug)
    units = property_obj.units.filter(is_available=True)

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        message = request.POST.get('message', '').strip()
        unit_id = request.POST.get('unit_id') or None
        unit = None
        if unit_id:
            unit = Unit.objects.filter(pk=unit_id, property=property_obj).first()

        application = Application.objects.create(
            property=property_obj,
            unit=unit,
            full_name=full_name,
            email=email,
            phone=phone,
            message=message,
        )
        return redirect(reverse('application_submitted') + f'?app_id={application.id}')

    return render(request, 'main/apply_for_property.html', {
        'property': property_obj,
        'units': units,
    })


def application_submitted(request):
    app_id = request.GET.get('app_id')
    application = None
    if app_id:
        application = Application.objects.filter(pk=app_id).first()
    return render(request, 'main/application_submitted.html', {'application': application})


@login_required
def owner_dashboard(request):
    owner_profile = get_object_or_404(OwnerProfile, user=request.user)
    properties = owner_profile.properties.all().prefetch_related('photos', 'units', 'applications')
    background_requests = BackgroundCheckRequest.objects.filter(
        application__property__owner=owner_profile
    ).select_related('application', 'application__property')
    documents = owner_profile.documents.all()
    return render(request, 'main/owner_dashboard.html', {
        'owner_profile': owner_profile,
        'properties': properties,
        'background_requests': background_requests,
        'documents': documents,
    })


@login_required
def manage_property_photos(request, property_id):
    owner_profile = get_object_or_404(OwnerProfile, user=request.user)
    property_obj = get_object_or_404(Property, pk=property_id, owner=owner_profile)

    if request.method == 'POST':
        if 'add_photo' in request.POST:
            image_url = request.POST.get('image_url', '').strip()
            is_primary = bool(request.POST.get('is_primary'))
            if image_url:
                photo = PropertyPhoto.objects.create(
                    property=property_obj,
                    image_url=image_url,
                    is_primary=is_primary,
                )
                if is_primary:
                    PropertyPhoto.objects.filter(property=property_obj).exclude(pk=photo.pk).update(is_primary=False)
        elif 'set_primary' in request.POST:
            photo_id = request.POST.get('photo_id')
            photo = get_object_or_404(PropertyPhoto, pk=photo_id, property=property_obj)
            photo.is_primary = True
            photo.save()
        elif 'delete_photo' in request.POST:
            photo_id = request.POST.get('photo_id')
            PropertyPhoto.objects.filter(pk=photo_id, property=property_obj).delete()

        return redirect('manage_property_photos', property_id=property_obj.id)

    photos = property_obj.photos.all()
    return render(request, 'main/manage_property_photos.html', {
        'property': property_obj,
        'photos': photos,
    })


@login_required
def manage_owner_documents(request):
    owner_profile = get_object_or_404(OwnerProfile, user=request.user)

    if request.method == 'POST':
        if 'add_document' in request.POST:
            title = request.POST.get('title', '').strip()
            document_type = request.POST.get('document_type', 'other')
            document_url = request.POST.get('document_url', '').strip()
            show_to_public = bool(request.POST.get('show_to_public'))
            show_to_applicants = bool(request.POST.get('show_to_applicants'))
            show_to_residents = bool(request.POST.get('show_to_residents'))
            if title and document_url:
                OwnerDocument.objects.create(
                    owner=owner_profile,
                    title=title,
                    document_type=document_type,
                    document_url=document_url,
                    show_to_public=show_to_public,
                    show_to_applicants=show_to_applicants,
                    show_to_residents=show_to_residents,
                )
        elif 'delete_document' in request.POST:
            doc_id = request.POST.get('doc_id')
            OwnerDocument.objects.filter(pk=doc_id, owner=owner_profile).delete()

        return redirect('manage_owner_documents')

    documents = owner_profile.documents.all()
    return render(request, 'main/manage_owner_documents.html', {
        'owner_profile': owner_profile,
        'documents': documents,
    })


@login_required
def run_background_check(request, application_id):
    application = get_object_or_404(Application, pk=application_id)
    owner_profile = get_object_or_404(OwnerProfile, user=request.user)
    if application.property.owner != owner_profile:
        return redirect('owner_dashboard')

    BackgroundCheckRequest.objects.create(
        application=application,
        status='pending_not_connected',
    )

    return render(request, 'main/background_check_requested.html', {
        'application': application,
    })
    })
