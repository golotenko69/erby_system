from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from django.shortcuts import render

from erbu_main.models import Student


# Create your views here.
def index_view(request):
    return render(request, 'erbu_main/index.html')

def about_view(request):
    return render(request, 'erbu_main/about.html')

def students_view(request):
    return render(request, 'erbu_main/students.html')

def contacts_view(request):
    return render(request, 'erbu_main/contacts.html')

class StudentsListView(ListView):
    model = Student
    template_name = 'erbu_main/students/students.html'
    context_object_name = 'students'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset