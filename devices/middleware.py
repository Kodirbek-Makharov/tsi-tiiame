from django.contrib.auth.decorators import login_required

def login_exempt(view):
    view.login_exempt = True
    return view


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        if getattr(view_func, 'login_exempt', False):
            return

        if request.user.is_authenticated:
            return

        return login_required(view_func)(request, *view_args, **view_kwargs)
