from django.http import Http404
from django_statsd.clients import get_client
import inspect
import time


class GraphiteMiddleware(object):

    def process_response(self, request, response):
        statsd = get_client().pipeline()
        statsd.incr('response.%s' % response.status_code, count=6)
        if hasattr(request, 'user') and request.user.is_authenticated():
            statsd.incr('response.auth.%s' % response.status_code, count=6)
        statsd.send()
        return response

    def process_exception(self, request, exception):
        if not isinstance(exception, Http404):
            statsd = get_client().pipeline()
            statsd.incr('response.500', count=6)
            if hasattr(request, 'user') and request.user.is_authenticated():
                statsd.incr('response.auth.500', count=6)
            statsd.send()


class GraphiteRequestTimingMiddleware(object):
    """statsd's timing data per view."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        view = view_func
        if not inspect.isfunction(view_func):
            view = view.__class__
        try:
            request._view_module = view.__module__
            request._view_name = view.__name__
            request._start_time = time.time()
        except AttributeError:
            pass

    def process_response(self, request, response):
        self._record_time(request)
        return response

    def process_exception(self, request, exception):
        self._record_time(request)

    def _record_time(self, request):
        if hasattr(request, '_start_time'):
            statsd = get_client().pipeline()
            ms = int((time.time() - request._start_time) * 1000)
            data = dict(module=request._view_module, name=request._view_name,
                        method=request.method)
            statsd.timing('view.{module}.{name}.{method}'.format(**data), ms)
            statsd.timing('view.{module}.{method}'.format(**data), ms)
            statsd.timing('view.{method}'.format(**data), ms)

            # Track requests above certain threshholds
            for threshhold in range(5, 16, 5):
                if ms > threshhold * 1000:
                    statsd.incr('view.{module}.{name}.{method}.over_{time}'
                                .format(time=threshhold, **data), count=6)
                else:
                    # Won't be larger than already larger numbers
                    break
            statsd.send()


class TastyPieRequestTimingMiddleware(GraphiteRequestTimingMiddleware):
    """statd's timing specific to Tastypie."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        try:
            request._view_module = view_kwargs['api_name']
            request._view_name = view_kwargs['resource_name']
            request._start_time = time.time()
        except (AttributeError, KeyError):
            super(TastyPieRequestTimingMiddleware, self).process_view(request,
                view_func, view_args, view_kwargs)
