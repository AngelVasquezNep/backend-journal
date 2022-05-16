from datetime import datetime
from django.db import models


class User(models.Model):
    first_name = models.CharField(null=False, max_length=30, default='john')
    last_name = models.CharField(null=False, max_length=30, default='doe')
    dob = models.DateField(null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Instructor(User):
    full_time = models.BooleanField(default=True)
    total_learners = models.IntegerField()

    def __str__(self):
        return f"First name: {self.first_name}, " +\
            f"Last name: {self.last_name}, " +\
            f"Is full time: {str(self.full_time)}, " +\
            f"Total Learners: {str(self.total_learners)}"


class Learner(User):
    STUDENT = 'student'
    DEVELOPER = 'developer'
    DATA_SCIENTIST = 'data_scientist'
    DATABASE_ADMIN = 'dba'
    OCCUPATION_CHOICES = [
        (STUDENT, 'Student'),
        (DEVELOPER, 'Developer'),
        (DATA_SCIENTIST, 'Data Scientist'),
        (DATABASE_ADMIN, 'Database Admin')
    ]
    occupation = models.CharField(
        null=False,
        max_length=20,
        choices=OCCUPATION_CHOICES,
        default=STUDENT
    )
    social_link = models.URLField(max_length=200)

    def __str__(self):
        return f"{super().__str__()} is {self.occupation}"


class Course(models.Model):
    name = models.CharField(null=False, max_length=100,
                            default='Online course')
    description = models.CharField(max_length=500)
    instructors = models.ManyToManyField(Instructor)
    pub_date = models.DateField(default=datetime.now)
    total_enrollment = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Name: {self.name}, Description: {self.description}"


class Lesson(models.Model):
    title = models.CharField(max_length=200, default="title")
    course = models.ForeignKey(Course, null=True, on_delete=models.CASCADE)
    content = models.TextField()

    def __str__(self):
        return f'{self.title} | {self.course}'


class Enrollment(models.Model):
    AUDIT = 'audit'
    HONOR = 'honor'
    COURSE_MODES = [
        (AUDIT, 'Audit'),
        (HONOR, 'Honor'),
    ]
    learner = models.ForeignKey(Learner, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date_enrolled = models.DateField(default=datetime.now)
    mode = models.CharField(max_length=5, choices=COURSE_MODES, default=AUDIT)
    is_approved = models.BooleanField(default=False, blank=False, null=False)
    submitted_at = models.DateField(null=True)

    def evalute_submission(self):
        last_submission = self.submissions.last()
        if not last_submission:
            return self.is_approved
        anwsers = [option.answer for option in last_submission.submission_options.all()]
        is_approved = enrollment.course.exam.review(anwsers)
        self.is_approved = is_approved
        self.save()
        return self.is_approved


class Submission(models.Model):
    enrollment = models.ForeignKey(
        Enrollment,
        related_name='submissions',
        on_delete=models.CASCADE,
    )
    submitted_at = models.DateField(default=datetime.now)

class SubmissionAnwers(models.Model):
    submission = models.ForeignKey(
        Submission,
        related_name='submission_options',
        on_delete=models.CASCADE,
    )
    answer = models.OneToOneField(
        'Option',
        related_name='+',
        on_delete=models.CASCADE,
    )

class Exam(models.Model):
    title = models.TextField(max_length=200, blank=False, null=False)
    min_score = models.PositiveIntegerField(default=1, blank=False, null=False)
    course = models.OneToOneField(
        'core.Course',
        related_name='exam',
        null=True,
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return self.title

    def review(self, answers):
        score = 0
        for answer in answers:
            if answer.is_answer:
                score += 1
        return score >= self.min_score

class Question(models.Model):
    exam = models.ForeignKey(
        "core.Exam",
        related_name="questions",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=200, blank=False, null=False)

    def __str__(self):
        return self.title


class Option(models.Model):
    question = models.ForeignKey(
        "core.Question",
        related_name="question_options",
        on_delete=models.CASCADE,
    )
    label = models.CharField(max_length=200, blank=False, null=False)
    value = models.CharField(max_length=100, blank=False, null=False)
    is_answer = models.SmallIntegerField(blank=False, null=False)

    def __str__(self):
        return f'{self.label}'
