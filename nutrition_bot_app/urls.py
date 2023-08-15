from django.urls import path
from . import views

urlpatterns = [
    path('calculate_calories/', views.calculate_calories, name='calculate_calories'),
]
