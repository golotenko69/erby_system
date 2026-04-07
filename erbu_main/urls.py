from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('contacts/', views.contacts_view, name='contacts'),
    path('about/', views.about_view, name='about'),
    path('students/', views.StudentsListView.as_view(), name='students'),

]