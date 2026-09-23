from django import forms
from django.core.exceptions import ValidationError
from .models import Category, Location, Client, Product, Asset, Event, Kit, KitComponent, Maintenance

def validate_photo(photo):
    if photo and photo.size > 5*1024*1024: raise ValidationError('A imagem deve ter até 5 MB.')
    if photo and getattr(photo,'image',None) and photo.image.format not in ['JPEG','PNG','WEBP']: raise ValidationError('Use JPEG, PNG ou WebP.')
    return photo

class Styled(forms.ModelForm):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-check-input' if isinstance(field.widget,forms.CheckboxInput) else 'form-control'
            if isinstance(field,forms.DateTimeField):
                field.widget = forms.DateTimeInput(format='%Y-%m-%dT%H:%M',attrs={'type':'datetime-local','class':'form-control'})
                field.input_formats = ['%Y-%m-%dT%H:%M']
            elif isinstance(field,forms.DateField): field.widget = forms.DateInput(format='%Y-%m-%d',attrs={'type':'date','class':'form-control'})
            if isinstance(field.widget,forms.Textarea): field.widget.attrs['rows'] = 3
    def clean_photo(self): return validate_photo(self.cleaned_data.get('photo'))

def factory(model,fields):
    return type(f'{model.__name__}Form',(Styled,),{'Meta':type('Meta',(),{'model':model,'fields':fields})})

CATALOG = {
 'categorias':(Category, factory(Category,['name','active']),'Categorias'),
 'locais':(Location,factory(Location,['name','active']),'Localizações'),
 'clientes':(Client,factory(Client,['name','contact','notes','active']),'Clientes'),
 'modelos':(Product,factory(Product,['name','category','kind','brand','model','minimum','notes','active']),'Modelos de equipamentos'),
 'equipamentos':(Asset,factory(Asset,['code','product','location','serial','photo','acquired','value','condition','notes','active']),'Equipamentos'),
 'kits':(Kit,factory(Kit,['name','notes','active']),'Kits'),
}
EventForm = factory(Event,['name','client','place','contact','manager','team','withdrawal','assembly','start','end','expected_return','release','notes'])
ComponentForm = factory(KitComponent,['kit','product','quantity'])
MaintenanceForm = factory(Maintenance,['asset','quantity','kind','reason','provider','expected','cost','photo'])

class MovementForm(forms.Form):
    request_key = forms.UUIDField(required=False)
    action = forms.ChoiceField(choices=[(x,x) for x in ['separate','dispatch','return','clear','damage','loss','consume','waive']])
    quantity = forms.IntegerField(min_value=1)
    reason = forms.CharField(required=False,max_length=3000)
    photo = forms.ImageField(required=False,validators=[validate_photo])

class RangeForm(forms.Form):
    start = forms.DateTimeField(label='Retirada',widget=forms.DateTimeInput(attrs={'type':'datetime-local','class':'form-control'}))
    end = forms.DateTimeField(label='Liberação',widget=forms.DateTimeInput(attrs={'type':'datetime-local','class':'form-control'}))
    def clean(self):
        data=super().clean()
        if data.get('start') and data.get('end') and data['end'] <= data['start']: raise ValidationError('A liberação deve ser posterior à retirada.')
        return data


class AssetForm(Styled):
    class Meta:
        model = Asset
        fields = ['code','product','location','serial','photo','acquired','value','condition','notes','active']
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['code'].required=False
        self.fields['code'].disabled=True
        self.fields['code'].help_text='Gerado ao salvar: EQ-000001. Código permanente; cadastros antigos preservam suas etiquetas.'
    def clean_code(self):
        return self.instance.code if self.instance.pk else ''

CATALOG['equipamentos']=(Asset,AssetForm,'Equipamentos')

class LabelPhotoForm(forms.Form):
    photo=forms.ImageField(label='Foto da etiqueta',widget=forms.ClearableFileInput(attrs={'class':'form-control','accept':'image/jpeg,image/png,image/webp','capture':'environment'}),validators=[validate_photo])

class LabelPrintForm(forms.Form):
    assets=forms.ModelMultipleChoiceField(label='Equipamentos',queryset=Asset.objects.none(),widget=forms.CheckboxSelectMultiple)
    layout=forms.ChoiceField(label='Formato',choices=[('a4','A4 · etiquetas 90 × 40 mm (papel sem gabarito pré-cortado)'),('thermal','Térmica · 90 × 40 mm')])
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['assets'].queryset=Asset.objects.filter(active=True).select_related('product').order_by('code')
    def clean_assets(self):
        qs=self.cleaned_data['assets']
        if qs.count()>100: raise ValidationError('Selecione no máximo 100 etiquetas por impressão.')
        return qs
