from django.contrib import admin
from django.contrib.auth import views as auth
from django.urls import path
from inventory import views as v
urlpatterns=[
 path('healthz/',v.health,name='health'),path('etiquetas/',v.label_print,name='label_print'),path('identificar/',v.label_scan,name='label_scan'),
 path('admin/',admin.site.urls),path('entrar/',auth.LoginView.as_view(),name='login'),path('sair/',auth.LogoutView.as_view(),name='logout'),
 path('',v.dashboard,name='dashboard'),path('eventos/',v.events,name='events'),path('eventos/novo/',v.event_edit,name='event_new'),path('eventos/<int:pk>/',v.event_detail,name='event'),path('eventos/<int:pk>/editar/',v.event_edit,name='event_edit'),path('eventos/<int:pk>/acao/',v.event_action,name='event_action'),path('eventos/<int:pk>/ocorrencia/',v.occurrence,name='occurrence'),path('itens/<int:pk>/acao/',v.line_action,name='line_action'),
 path('cadastros/<str:kind>/',v.catalog,name='catalog'),path('cadastros/<str:kind>/novo/',v.catalog_edit,name='catalog_new'),path('cadastros/<str:kind>/<int:pk>/editar/',v.catalog_edit,name='catalog_edit'),path('kits/<int:pk>/componentes/',v.component,name='component'),
 path('equipamento/<uuid:token>/',v.asset_detail,name='asset'),path('equipamento/<uuid:token>/ajuste/',v.adjust,name='adjust'),path('equipamento/<uuid:token>/qr/',v.qr,name='qr'),
 path('disponibilidade/',v.availability,name='availability'),path('manutencao/',v.maintenance,name='maintenance'),path('manutencao/nova/',v.maintenance_new,name='maintenance_new'),path('manutencao/<int:pk>/liberar/',v.maintenance_close,name='maintenance_close'),
 path('operacao/<str:mode>/',v.queue,name='queue'),path('relatorios/',v.reports,name='reports'),path('ajuda/',v.help_page,name='help'),path('arquivo/<str:kind>/<int:pk>/',v.private_media,name='private_media'),
]
