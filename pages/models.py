from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Property(models.Model):
    PROPERTY_TYPES = [
        ('house', 'Single Family Home'),
        ('apartment', 'Apartment'),
        ('condo', 'Condo'),
        ('townhouse', 'Townhouse'),
        ('land', 'Land'),
    ]

    title = models.CharField(max_length=200)
    property_type = models.CharField(max_length=20, choices=PROPERTY_TYPES)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    bedrooms = models.IntegerField()
    bathrooms = models.IntegerField()
    sqft = models.IntegerField()
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    zip = models.CharField(max_length=20)
    description = models.TextField()
    image_url = models.URLField(max_length=1024, blank=True, default='')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.city}"


class VisitRequest(models.Model):
    """Stores a user's request to schedule a property visit."""
    # Optional link to user if logged in at the time of submission
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='visit_requests')

    # Optional context about the property
    property_title = models.CharField(max_length=200, blank=True, default='')
    property_address = models.CharField(max_length=255, blank=True, default='')

    # Requester details
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40)

    # Preferred schedule
    date = models.DateField()
    time = models.TimeField()

    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        base = self.name or 'Visitor'
        when = f"{self.date} {self.time}"
        addr = f" @ {self.property_address}" if self.property_address else ''
        return f"VisitRequest({base} {when}{addr})"
class ContactMessage(models.Model):
    """Stores a message from the contact form."""
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True, default='')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} ({self.email}) - {'Read' if self.is_read else 'New'}"
