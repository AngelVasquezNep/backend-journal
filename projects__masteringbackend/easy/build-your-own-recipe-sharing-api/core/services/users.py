from django.contrib.auth import get_user_model

User = get_user_model()


class CreateUserService:
    @staticmethod
    def create_user(
        username,
        email,
        password=None,
        first_name=None,
        last_name=None,
        is_active=True,
        is_superuser=True,
    ):
        user = User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=is_active,
            is_superuser=is_superuser,
        )

        if password:
            user.set_password(password)
            user.save()

        return user

    @staticmethod
    def create_client_user(
        username,
        email,
        password,
        first_name=None,
        last_name=None,
    ):
        return CreateUserService.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            is_superuser=False,
        )
