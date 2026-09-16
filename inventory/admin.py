from django.contrib import admin
from .models import Category,Location,Client,Product,Asset,Event,Kit,KitComponent,EventLine,Maintenance,Audit
# Operações passam exclusivamente pelos serviços; admin não altera saldos nem históricos.
class ReadOnly(admin.ModelAdmin):
    def has_add_permission(self,request): return False
    def has_change_permission(self,request,obj=None): return False
    def has_delete_permission(self,request,obj=None): return False
for model in [Category,Location,Client,Product,Asset,Event,Kit,KitComponent,EventLine,Maintenance,Audit]: admin.site.register(model,ReadOnly)
admin.site.site_header='Palco · Administração'
