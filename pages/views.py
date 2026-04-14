from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse, HttpResponseBadRequest
from django.urls import reverse
from .models import Property, VisitRequest, ContactMessage
from django.views.decorators.http import require_POST
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.forms import UserCreationForm


def home(request):
    latest_properties = Property.objects.order_by('-created_at')[:4]
    return render(request, 'index.html', {'featured_properties': latest_properties})


def properties(request):
    q = (request.GET.get('q') or '').strip()
    props = Property.objects.all()
    if q:
        props = props.filter(models.Q(city__icontains=q) | models.Q(zip__icontains=q))
    props = props.order_by('-created_at')
    return render(request, 'properties.html', {"properties": props, "q": q})


def agents(request):
    return render(request, 'agents.html')


from django.contrib import messages

@login_required(login_url='login')
def sell(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        property_type = request.POST.get('property_type', '').strip()
        price = request.POST.get('price', '').strip()
        bedrooms = request.POST.get('bedrooms', '').strip()
        bathrooms = request.POST.get('bathrooms', '').strip()
        sqft = request.POST.get('sqft', '').strip()
        address = request.POST.get('address', '').strip()
        city = request.POST.get('city', '').strip()
        zip_code = request.POST.get('zip', '').strip()
        description = request.POST.get('description', '').strip()
        image_file = request.FILES.get('image_url')

        image_url_str = ''
        if image_file:
            from backend.supabase_client import upload_to_supabase
            import uuid
            import os
            ext = os.path.splitext(image_file.name)[1]
            unique_name = f"property_{uuid.uuid4().hex[:8]}{ext}"
            try:
                image_url_str = upload_to_supabase(image_file, unique_name, folder="properties")
            except Exception as e:
                messages.error(request, f"Image upload failed: {e}")
                return render(request, 'sell.html')

        if not all([title, property_type, price, bedrooms, bathrooms, sqft, address, city, zip_code, description]):
            if not image_url_str: # Prevent error if image is missing but ignore if handled
                pass
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'sell.html')

        try:
            prop = Property.objects.create(
                title=title,
                property_type=property_type,
                price=price,
                bedrooms=int(bedrooms),
                bathrooms=int(bathrooms),
                sqft=int(sqft),
                address=address,
                city=city,
                zip=zip_code,
                description=description,
                image_url=image_url_str,
                created_by=request.user,
            )
            messages.success(request, f"Property '{title}' has been listed successfully!")
        except Exception as e:
            messages.error(request, f"Error saving property: {e}")
            return render(request, 'sell.html')

        return redirect('properties')

    return render(request, 'sell.html')


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        message = request.POST.get('message', '').strip()

        if not all([name, email, message]):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Please fill in all required fields.'}, status=400)
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'contact.html')

        try:
            # Simple deduplication: Check for same context within last 2 minutes
            from django.utils import timezone
            from datetime import timedelta
            recent_exists = ContactMessage.objects.filter(
                name=name, email=email, message=message,
                created_at__gte=timezone.now() - timedelta(minutes=2)
            ).exists()
            
            if not recent_exists:
                ContactMessage.objects.create(
                    name=name,
                    email=email,
                    phone=phone,
                    message=message
                )
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': 'Message received!'})
            messages.success(request, 'Message sent successfully!')
            return redirect('contact')
        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=500)
            messages.error(request, f'Error sending message: {e}')

    return render(request, 'contact.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            # If staff/superuser, go to admin dashboard
            if user.is_staff or user.is_superuser:
                try:
                    return redirect('admin_dashboard')
                except Exception:
                    return redirect('/admin/')
            # Otherwise, continue to next or home
            next_url = request.GET.get('next') or 'home'
            return redirect(next_url)
        return render(request, 'login.html', {"error": "Invalid credentials"})
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('home')


def signup_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')
            # Phone could go into a custom profile model, but for now we skip storing it without a profile table
            user.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            next_url = request.GET.get('next') or 'home'
            return redirect(next_url)
        return render(request, 'signup.html', {'form': form, 'error': 'Please correct the errors below.'})
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})


def schedule_visit(request):
    """
    Simple schedule visit page.
    GET: render the form
    POST: validate basic fields and show success message
    """
    if request.method == 'POST':
        name = (request.POST.get('name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        phone = (request.POST.get('phone') or '').strip()
        date = (request.POST.get('date') or '').strip()
        time = (request.POST.get('time') or '').strip()
        notes = (request.POST.get('notes') or '').strip()
        property_address = (request.POST.get('property_address') or '').strip()
        property_title = (request.POST.get('property_title') or '').strip()

        errors = []
        if not name: errors.append('Full name is required.')
        if not email: errors.append('Email is required.')
        if not phone: errors.append('Phone is required.')
        if not date: errors.append('Preferred date is required.')
        if not time: errors.append('Preferred time is required.')

        if errors:
            return render(request, 'schedule_visit.html', {
                'errors': errors,
                'form': {
                    'name': name,
                    'email': email,
                    'phone': phone,
                    'date': date,
                    'time': time,
                    'notes': notes,
                    'property_address': property_address,
                    'property_title': property_title,
                }
            })

        # Persist to DB
        VisitRequest.objects.create(
            user=request.user if request.user.is_authenticated else None,
            property_title=property_title,
            property_address=property_address,
            name=name,
            email=email,
            phone=phone,
            date=date,
            time=time,
            notes=notes,
        )

        return render(request, 'schedule_visit.html', {
            'success': 'Your visit has been scheduled! We will confirm shortly.',
        })
    # GET: Allow prefill via query params
    initial = {
        'property_address': (request.GET.get('address') or '').strip(),
        'property_title': (request.GET.get('title') or '').strip(),
    }
    return render(request, 'schedule_visit.html', {'form': initial})

def admin_dashboard(request):
    """
    Custom elite dashboard for high-level management.
    """
    if not request.user.is_staff:
        return redirect('login')
        
    from django.contrib.auth.models import User
    
    context = {
        'total_properties': Property.objects.count(),
        'total_visits': VisitRequest.objects.count(),
        'total_users': User.objects.count(),
        'recent_properties': Property.objects.order_by('-created_at')[:10],
        'recent_visits': VisitRequest.objects.order_by('-created_at')[:10],
        'recent_messages': ContactMessage.objects.order_by('-created_at')[:10],
        'all_users': User.objects.all().order_by('-date_joined')[:10],
    }
    return render(request, 'admin_dashboard.html', context)
@login_required(login_url='login')
def mark_message_read(request, message_id):
    if not request.user.is_staff:
        return redirect('login')
    
    try:
        msg = ContactMessage.objects.get(id=message_id)
        msg.is_read = True
        msg.save()
    except ContactMessage.DoesNotExist:
        pass
    
    return redirect('admin_dashboard')
