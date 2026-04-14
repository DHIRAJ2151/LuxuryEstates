from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('properties/', views.properties, name='properties'),
    path('agents/', views.agents, name='agents'),
    path('sell/', views.sell, name='sell'),
    path('contact/', views.contact, name='contact'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_view, name='signup'),
    path('schedule/', views.schedule_visit, name='schedule_visit'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/read/<int:message_id>/', views.mark_message_read, name='mark_message_read'),
]
