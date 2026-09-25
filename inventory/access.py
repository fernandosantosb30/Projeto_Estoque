from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Event
from django.conf import settings

def role(user):
    if not user.is_authenticated: return ''
    if user.is_superuser: return 'Administrador'
    for name in ['Administrador','Gestor','Estoque','Equipe operacional']:
        if user.groups.filter(name=name).exists(): return name
    return ''

def require(user, allowed):
    if role(user) not in ['Administrador',*allowed]: raise PermissionDenied('Seu perfil não permite esta operação.')

def access(*allowed):
    def decorator(fn):
        @login_required
        @wraps(fn)
        def wrapped(request,*args,**kwargs):
            require(request.user,allowed)
            return fn(request,*args,**kwargs)
        return wrapped
    return decorator

def events_for(user):
    qs = Event.objects.all()
    if role(user) == 'Equipe operacional': qs = qs.filter(Q(team=user)|Q(manager=user)).distinct()
    return qs

def navigation(request):
    r = role(request.user)
    return {'user_role':r,'can_manage':r in ['Administrador','Gestor'],'can_operate':r in ['Administrador','Gestor','Estoque'],'demo_mode':settings.DEMO_MODE}
