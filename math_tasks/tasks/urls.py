from django.urls import path
from . import views

urlpatterns = [
    path('', views.start_view, name='main'),
    path('quiz/', views.quiz_view, name='quiz'),
    path('result/', views.result_view, name='result'),
]