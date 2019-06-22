
from functools import wraps

def test_decorator(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print("Decoration Function")
        return f(*args, **kwargs)

    return decorated_function

@test_decorator
def func():
    print("Calling func function")
