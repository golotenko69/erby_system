from django.urls import path

from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('contacts/', views.contacts_view, name='contacts'),
    path('students/', views.StudentsListView.as_view(), name='students'),
    path('student_detail/<int:student_id>/', views.StudentDetailView.as_view(), name='student_detail'),
    path('student/add/', views.StudentCreateView.as_view(), name='student_add'),
    path('student/<int:student_id>/edit/', views.StudentFullEditView.as_view(), name='student_edit'),
    path('student/<int:student_id>/delete/', views.StudentDeleteView.as_view(), name='student_delete'),
    path('institutions/', views.EducationInstitutionListView.as_view(), name='institutions'),
    path('institution/add/', views.EducationInstitutionCreateView.as_view(), name='institution_add'),
    path('institution/<int:institution_id>/', views.EducationInstitutionDetailView.as_view(), name='institution_detail'),
    path('institution/<int:institution_id>/edit/', views.EducationInstitutionUpdateView.as_view(), name='institution_edit'),
    path('students/export/excel/', views.ExportStudentsExcelView.as_view(), name='student_export_excel'),
    path('institution/<int:institution_id>/delete/', views.EducationInstitutionDeleteView.as_view(), name='institution_delete'),
    path('logs/mark-read/', views.mark_logs_read, name='mark_logs_read'),
    path('logs/api/<int:log_id>/', views.LogDetailJsonView.as_view(), name='log_detail_api'),
]