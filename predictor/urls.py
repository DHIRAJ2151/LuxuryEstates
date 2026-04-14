from django.urls import path
from .views import predict_price, house_price_predict, chatbot

app_name = 'predictor'

urlpatterns = [
    path('predict/', predict_price, name='predict_price'),
    path('predict-price/', house_price_predict, name='house_price_predict'),
    path('api/chatbot/', chatbot, name='chatbot'),
]
