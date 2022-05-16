from core.models import (
    Enrollment,
    Submission,
    SubmissionAnwers,
)


def simulate_all_good():
    enrollment = Enrollment.objects.first()
    submission = Submission.objects.create(enrollment=enrollment)

    for question in enrollment.course.exam.questions.all():
        for question_option in question.question_options.filter(is_answer=True):
            SubmissionAnwers.objects.get_or_create(
                submission=submission,
                answer=question_option,
            )

    print(f'{enrollment} | Approved: {enrollment.is_approved}')
    is_approved = enrollment.evalute_submission()
    print(f'{enrollment} | Approved: {is_approved}')
