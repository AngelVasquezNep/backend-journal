from datetime import date
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from core.models import Course


def course_list(request):
    course = Course.objects.first()
    if course:
        template = f"""
          <html>
            <body>
              <h1>The first course is {course.name}</h1>
            </body>
          </html>
        """

        return HttpResponse(content=template)
    return HttpResponse(status=400, content="Course not found")


def get_date(request):
    today = date.today()
    template = f"""<html>
                Today's date is {today}
               </html>"""
    return HttpResponse(content=template)


def index(request):
    courses = Course.objects.all()
    context = {
        'course_list': courses
    }
    return render(request, 'core/courses.html', context)


def enroll(request, course_id):
    # If request method is POST
    if request.method == 'POST':
        # First try to read the course object
        # If could be found, raise a 404 exception
        course = get_object_or_404(Course, pk=course_id)
        # Increase the enrollment by 1
        course.total_enrollment += 1
        course.save()
        # Return a HTTP response redirecting user to course list view
        return HttpResponseRedirect(reverse(viewname='courses:course_list'))
