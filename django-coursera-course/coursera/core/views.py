from datetime import date
from django import views
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.contrib.auth import logout, authenticate, login, get_user_model

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
        return HttpResponseRedirect(reverse(viewname='courses:course', args=(course.id,)))


class CourseListView(views.View):
    # Handles get request
    def get(self, request):
        context = {}
        course_list = Course.objects.order_by('-total_enrollment')[:10]
        context['course_list'] = course_list
        return render(request, 'core/courses.html', context)


class EnrollView(views.View):

    # Handles post request
    def post(self, request, course_id=None, *args, **kwargs):
        course = get_object_or_404(Course, pk=course_id)
        # Increase total enrollment by 1
        course.total_enrollment += 1
        course.save()
        return HttpResponseRedirect(reverse(viewname='courses:course', args=(course.id,)))


class CourseDetailsView(views.View):

    # Handles get request
    def get(self, request, course_id=None, *args, **kwargs):
        course = Course.objects.filter(pk=course_id).first()
        context = {
            'course': course
        }
        return render(request, 'core/course.html', context)

def logout_request(request):
    # Get the user object based on session id in request
    print("Log out the user `{}`".format(request.user.username))
    # Logout user in the request
    logout(request)
    # Redirect user back to course list view
    return redirect('courses:popular_course_list')

def login_request(request):
    context = {}
    # Handles POST request
    if request.method == "POST":
        # Get username and password from request.POST dictionary
        username = request.POST['username']
        password = request.POST['psw']
        # Try to check if provide credential can be authenticated
        user = authenticate(username=username, password=password)
        if user is not None:
            # If user is valid, call login method to login current user
            login(request, user)
            return redirect('courses:popular_course_list')
        else:
            # If not, return to login page again
            return render(request, 'core/user_login.html', context)
    else:
        return render(request, 'core/user_login.html', context)


def registration_request(request):
    context = {}
    # If it is a GET request, just render the registration page
    if request.method == 'GET':
        return render(request, 'core/user_registration.html', context)
    # If it is a POST request
    elif request.method == 'POST':
        # Get user information from request.POST
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        User = get_user_model()
        try:
            # Check if user already exists
            User.objects.get(username=username)
            user_exist = True
        except:
            # If not, simply log this is a new user
            print("{} is new user".format(username))
        # If it is a new user
        if not user_exist:
            # Create user in auth_user table
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            # Login the user and redirect to course list page
            login(request, user)
            return redirect("courses:popular_course_list")
        else:
            return render(request, 'core/user_registration.html', context)