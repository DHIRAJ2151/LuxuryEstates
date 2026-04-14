from django.contrib import admin
from .models import Property, VisitRequest, ContactMessage

from django import forms
from backend.supabase_client import upload_to_supabase
import uuid
import os

class PropertyAdminForm(forms.ModelForm):
    image_file = forms.ImageField(required=False, label="Upload Property Image")

    class Meta:
        model = Property
        fields = '__all__'
        exclude = ('image_url',)

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    form = PropertyAdminForm
    list_display = ("title", "city", "price", "bedrooms", "bathrooms", "created_by", "created_at")
    list_filter = ("city", "property_type", "created_at")
    search_fields = ("title", "address", "city", "description")
    
    # Hide the created_by field from the UI as we set it automatically
    exclude = ('created_by', 'image_url')
    
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image_url:
            from django.utils.html import format_html
            return format_html('<img src="{}" style="max-height: 200px; border-radius: 8px; border: 1px solid #ddd;" />', obj.image_url)
        return "No Image Uploaded"
    image_preview.short_description = "Current Image Preview"

    def save_model(self, request, obj, form, change):
        # Handle the custom image_file from our form
        image_file = form.cleaned_data.get('image_file')
        if image_file:
            ext = os.path.splitext(image_file.name)[1]
            unique_name = f"property_{uuid.uuid4().hex[:8]}{ext}"
            try:
                # Upload to Supabase and get URL
                public_url = upload_to_supabase(image_file, unique_name, folder="properties")
                obj.image_url = public_url
            except Exception as e:
                self.message_user(request, f"Error uploading image: {e}", level='ERROR')
        
        # Set created_by to current user for new listings
        if not change or not obj.created_by:
            obj.created_by = request.user
            
        super().save_model(request, obj, form, change)

    def get_fields(self, request, obj=None):
        # Explicit order for better UI
        base_fields = ['title', 'property_type', 'price', 'bedrooms', 'bathrooms', 'sqft', 'address', 'city', 'zip', 'description', 'image_file']
        if obj and obj.image_url:
            base_fields.append('image_preview')
        return base_fields




@admin.register(VisitRequest)
class VisitRequestAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "date", "time", "property_address", "created_at")
    list_filter = ("date", "created_at")
    search_fields = ("name", "email", "phone", "property_address", "property_title", "notes")


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "email", "phone", "message")
