from datetime import date
from django.http import HttpResponse

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
