from datetime import datetime


def execution_time(func):
    def wrapper(*args, **kwargs):
        initial_time = datetime.now()
        result = func(*args, **kwargs)
        final_time = datetime.now()
        time_elapsed = final_time - initial_time

        print(f"Function executed in {time_elapsed.total_seconds()} seconds")

        return result

    return wrapper
