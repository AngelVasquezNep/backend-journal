from django.contrib.auth import get_user_model

User = get_user_model()


class CreateUser:
    @staticmethod
    def create_client_user(
        username,
        email,
        first_name,
        last_name,
        password=None,
    ):
        user = User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_superuser=False,
        )

        if password:
            user.set_password(password)
            user.save()

        return user
