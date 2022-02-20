from django.contrib import admin
from core.models import User, Instructor, Learner, Course, Lesson, Enrollment


class LessonInline(admin.StackedInline):
    model = Lesson 
    extra = 5         # How many Row Lessons should appear

class CourseAdmin(admin.ModelAdmin):
    fields = ['name', 'description', 'instructors', ]
    inlines = [LessonInline] # It appears Lesson "Model" fields
                             # Lesson Model has a Foreign key Course

class InstructorAdmin(admin.ModelAdmin):
    fields = ['first_name', 'last_name', 'full_time']


admin.site.register(Course, CourseAdmin)
admin.site.register(Instructor, InstructorAdmin)
admin.site.register([User, Learner, Lesson, Enrollment])
