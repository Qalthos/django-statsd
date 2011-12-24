from django import http
from django.conf import settings
from django_statsd.clients import statsd

boomerang ={
 'window.performance.navigation.redirectCount': 'nt_red_cnt',
 'window.performance.navigation.type': 'nt_nav_type',
 'window.performance.timing.connectEnd': 'nt_con_end',
 'window.performance.timing.connectStart': 'nt_con_st',
 'window.performance.timing.domComplete': 'nt_domcomp',
 'window.performance.timing.domContentLoaded': 'nt_domcontloaded',
 'window.performance.timing.domInteractive': 'nt_domint',
 'window.performance.timing.domLoading': 'nt_domloading',
 'window.performance.timing.domainLookupEnd': 'nt_dns_end',
 'window.performance.timing.domainLookupStart': 'nt_dns_st',
 'window.performance.timing.fetchStart': 'nt_fet_st',
 'window.performance.timing.loadEventEnd': 'nt_load_end',
 'window.performance.timing.loadEventStart': 'nt_load_st',
 'window.performance.timing.navigationStart': 'nt_nav_st',
 'window.performance.timing.redirectEnd': 'nt_red_end',
 'window.performance.timing.redirectStart': 'nt_red_st',
 'window.performance.timing.requestStart': 'nt_req_st',
 'window.performance.timing.responseEnd': 'nt_res_end',
 'window.performance.timing.responseStart': 'nt_res_st',
 'window.performance.timing.unloadEventEnd': 'nt_unload_end',
 'window.performance.timing.unloadEventStart': 'nt_unload_st'
}

types = {
 '0': 'navigate',
 '1': 'reload',
 '2': 'back_forward',
 '255': 'reserved'
}

# These are the default keys that we will try and record.
keys = [
 'window.performance.timing.domComplete',
 'window.performance.timing.domInteractive',
 'window.performance.timing.domLoading',
 'window.performance.navigation.redirectCount',
 'window.performance.navigation.type',
]

def _process_boomerang(request):
    if 'nt_nav_st' not in request.GET:
        raise ValueError, ('nt_nav_st not in request.GET, make sure boomerang'
            ' is made with navigation API timings as per the following'
            ' http://yahoo.github.com/boomerang/doc/howtos/howto-9.html')

    # This when the request started, everything else will be relative to this
    # for the purposes of statsd measurement.
    start = int(request.GET['nt_nav_st'])

    for k in getattr(settings, 'STATSD_RECORD_KEYS', keys):
        v = request.GET.get(boomerang[k])
        if not v or v == 'undefined':
            continue
        if k in boomerang:
            if 'timing' in k:
                # Some values will be zero. We want the output of that to
                # be zero relative to start.
                v = max(start, int(v)) - start
                statsd.timing(k, v)
            elif k == 'window.performance.navigation.type':
                statsd.incr('%s.%s' % (k, types[v]))
            elif k == 'window.performance.navigation.redirectCount':
                statsd.incr(k, int(v))

    return http.HttpResponse('recorded')


clients = {
 'boomerang': _process_boomerang,
}


def record(request):
    """
    This is a Django method you can link to in your URLs that process
    the incoming data. Be sure to add a client parameter into your request
    so that we can figure out how to process this request. For example
    if you are using boomerang, you'll need: client = boomerang.

    You can define a method in STATSD_RECORD_GUARD that will do any lookup
    you need for imposing security on this method, so that not just anyone
    can post to it.
    """
    if 'client' not in request.REQUEST:
        raise ValueError, 'No client specified in the REQUEST.'
    client = request.REQUEST['client']
    if client not in clients:
        raise ValueError, 'Client %s not known.' % client


    guard = getattr(settings, 'STATSD_RECORD_GUARD', None)
    if guard:
        if not callable(guard):
            raise ValueError, 'STATSD_RECORD_GUARD must be callable'
        result = guard(request)
        if result:
            return result

    return clients[client](request)