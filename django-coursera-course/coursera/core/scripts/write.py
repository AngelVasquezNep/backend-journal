from datetime import date
from core.models import (
    User,
    Instructor,
    Course,
    Lesson,
    Learner,
    Enrollment,
    Exam,
    Question,
    Option,
)


def write_instructors():
    # Add instructors
    # Create a user
    user_john = User(first_name='John', last_name='Doe', dob=date(1962, 7, 16))
    user_john.save()
    instructor_john = Instructor(full_time=True, total_learners=30050)
    # Update the user reference of instructor_john to be user_john
    instructor_john.user = user_john
    instructor_john.save()

    instructor_yan = Instructor(first_name='Yan', last_name='Luo', dob=date(
        1962, 7, 16), full_time=True, total_learners=30050)
    instructor_yan.save()

    instructor_joy = Instructor(first_name='Joy', last_name='Li', dob=date(
        1992, 1, 2), full_time=False, total_learners=10040)
    instructor_joy.save()
    instructor_peter = Instructor(first_name='Peter', last_name='Chen', dob=date(
        1982, 5, 2), full_time=True, total_learners=2002)
    instructor_peter.save()
    print("Instructor objects all saved... ")


def write_courses():
    # Add Courses
    course_cloud_app = Course(name="Cloud Application Development with Database",
                              description="Develop and deploy application on cloud")
    course_cloud_app.save()
    course_python = Course(name="Introduction to Python",
                           description="Learn core concepts of Python and obtain hands-on "
                                       "experience via a capstone project")
    course_python.save()

    print("Course objects all saved... ")


def write_lessons():
    # Add lessons
    lession1 = Lesson(title='Lesson 1',
                      content="Object-relational mapping project")
    lession1.save()
    lession2 = Lesson(title='Lesson 2', content="Django full stack project")
    lession2.save()
    print("Lesson objects all saved... ")


def write_learners():
    # Add Learners
    learner_james = Learner(first_name='James', last_name='Smith', dob=date(1982, 7, 16),
                            occupation='data_scientist',
                            social_link='https://www.linkedin.com/james/')
    learner_james.save()
    learner_mary = Learner(first_name='Mary', last_name='Smith', dob=date(1991, 6, 12), occupation='dba',
                           social_link='https://www.facebook.com/mary/')
    learner_mary.save()
    learner_robert = Learner(first_name='Robert', last_name='Lee', dob=date(1999, 1, 2), occupation='student',
                             social_link='https://www.facebook.com/robert/')
    learner_robert.save()
    learner_david = Learner(first_name='David', last_name='Smith', dob=date(1983, 7, 16),
                            occupation='developer',
                            social_link='https://www.linkedin.com/david/')
    learner_david.save()
    learner_john = Learner(first_name='John', last_name='Smith', dob=date(1986, 3, 16),
                           occupation='developer',
                           social_link='https://www.linkedin.com/john/')
    learner_john.save()
    print("Learner objects all saved... ")


def write_exams():
    course_cloud_app = Course.objects.get(name="Cloud Application Development with Database")
    exam = Exam.objects.create(
        title="Exam 1: Cloud Application Development with Database",
        course=course_cloud_app,
    )

    q1 = Question.objects.create(exam=exam, title="Which framework is used to build backend and frontend apps at the same time?")
    q2 = Question.objects.create(exam=exam, title="Does Django allow you to use templates")

    Option.objects.create(
        question=q1,
        label="Django",
        value="OPT_1",
        is_answer=True,
    )
    Option.objects.create(
        question=q1,
        label="Node.js",
        value="OPT_2",
        is_answer=False,
    )
    Option.objects.create(
        question=q2,
        label="Yes",
        value="OPT_3",
        is_answer=True,
    )
    Option.objects.create(
        question=q2,
        label="No",
        value="OPT_4",
        is_answer=False,
    )
    print("Exams objects all saved... ")


def create_enrollment():
    for course in Course.objects.all():
        learners = Learner.objects.all()
        enrollments = [Enrollment(learner=learner, course=course) for learner in learners]
        Enrollment.objects.bulk_create(enrollments)

def clean_data():
    # Delete all data to start from fresh
    Enrollment.objects.all().delete()
    User.objects.all().delete()
    Learner.objects.all().delete()
    Instructor.objects.all().delete()
    Course.objects.all().delete()
    Lesson.objects.all().delete()
    Exam.objects.all().delete()


def start_app():
    clean_data()
    write_courses()
    write_instructors()
    write_lessons()
    write_learners()
    write_exams()
    create_enrollment()

# from core.scripts.write import start_app