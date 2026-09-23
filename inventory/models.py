import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, F

class Named(models.Model):
    name = models.CharField('nome', max_length=160)
    active = models.BooleanField('ativo', default=True)
    class Meta:
        abstract = True
        ordering = ['name']
    def __str__(self): return self.name

class Category(Named):
    class Meta(Named.Meta): verbose_name = 'categoria'

class Location(Named):
    class Meta(Named.Meta): verbose_name = 'localização'

class Client(Named):
    contact = models.CharField('contato', max_length=200, blank=True)
    notes = models.TextField('observações', blank=True)
    class Meta(Named.Meta): verbose_name = 'cliente'

class Product(Named):
    KINDS = [('unit','Individual'),('bulk','Por quantidade'),('supply','Consumível')]
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='categoria')
    kind = models.CharField('controle', max_length=10, choices=KINDS)
    brand = models.CharField('marca', max_length=100, blank=True)
    model = models.CharField('modelo', max_length=100, blank=True)
    minimum = models.PositiveIntegerField('estoque mínimo', default=0)
    notes = models.TextField('observações', blank=True)
    class Meta(Named.Meta): verbose_name = 'modelo de equipamento'

class Asset(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    code = models.CharField('código', max_length=50, unique=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='modelo')
    location = models.ForeignKey(Location, on_delete=models.PROTECT, verbose_name='localização')
    serial = models.CharField('número de série', max_length=100, blank=True)
    photo = models.ImageField('foto', upload_to='assets/%Y/%m/', blank=True)
    acquired = models.DateField('data de aquisição', null=True, blank=True)
    value = models.DecimalField('valor de compra (R$)', max_digits=12, decimal_places=2, null=True, blank=True)
    condition = models.CharField('conservação', max_length=200, default='Bom')
    notes = models.TextField('observações', blank=True)
    active = models.BooleanField('ativo', default=True)
    total = models.PositiveIntegerField(default=0, editable=False)
    class Meta:
        ordering = ['product__category__name','location__name','code']
        verbose_name = 'equipamento / lote'
    def __str__(self): return f'{self.code} · {self.product.name}'
    @property
    def held(self): return sum(x.sent-x.cleared-x.written_off for x in self.lines.all())
    @property
    def repairing(self): return sum(x.quantity for x in self.maintenance.filter(closed_at__isnull=True))
    @property
    def available(self): return max(0, self.total-self.held-self.repairing) if self.active and self.product.active else 0

class Event(models.Model):
    STATUSES = [('draft','Rascunho'),('reserved','Reservado'),('picking','Em separação'),('out','Em operação'),('checking','Aguardando conferência'),('done','Concluído'),('cancelled','Cancelado')]
    name = models.CharField('nome do evento',max_length=200)
    client = models.ForeignKey(Client,on_delete=models.PROTECT,verbose_name='cliente')
    place = models.CharField('local do evento',max_length=250)
    contact = models.CharField('contato no local',max_length=200,blank=True)
    manager = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT,related_name='managed_events',verbose_name='responsável')
    team = models.ManyToManyField(settings.AUTH_USER_MODEL,blank=True,related_name='assigned_events',verbose_name='equipe')
    withdrawal = models.DateTimeField('retirada')
    assembly = models.DateTimeField('montagem')
    start = models.DateTimeField('início')
    end = models.DateTimeField('término')
    expected_return = models.DateTimeField('retorno previsto')
    release = models.DateTimeField('liberação prevista após conferência')
    status = models.CharField(max_length=15,choices=STATUSES,default='draft',editable=False)
    notes = models.TextField('observações',blank=True)
    class Meta:
        ordering = ['withdrawal']
        verbose_name = 'evento'
        constraints = [models.CheckConstraint(condition=Q(withdrawal__lte=F('assembly')) & Q(assembly__lte=F('start')) & Q(start__lt=F('end')) & Q(end__lte=F('expected_return')) & Q(expected_return__lte=F('release')), name='ordered_event_dates')]
    def __str__(self): return self.name
    def clean(self):
        dates = [self.withdrawal,self.assembly,self.start,self.end,self.expected_return,self.release]
        if all(dates) and (dates != sorted(dates) or self.start >= self.end):
            raise ValidationError('As datas devem seguir: retirada ≤ montagem ≤ início < término ≤ retorno ≤ liberação.')

class Kit(Named):
    notes = models.TextField('observações',blank=True)

class KitComponent(models.Model):
    kit = models.ForeignKey(Kit,on_delete=models.PROTECT,related_name='components')
    product = models.ForeignKey(Product,on_delete=models.PROTECT,verbose_name='modelo')
    quantity = models.PositiveIntegerField('quantidade',default=1)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['kit','product'],name='unique_kit_product'),models.CheckConstraint(condition=Q(quantity__gt=0),name='kit_positive')]
    def __str__(self): return f'{self.product} × {self.quantity}'

class EventLine(models.Model):
    event = models.ForeignKey(Event,on_delete=models.PROTECT,related_name='lines')
    asset = models.ForeignKey(Asset,on_delete=models.PROTECT,related_name='lines')
    quantity = models.PositiveIntegerField()
    separated = models.PositiveIntegerField(default=0)
    sent = models.PositiveIntegerField(default=0)
    returned = models.PositiveIntegerField(default=0)
    cleared = models.PositiveIntegerField(default=0)
    written_off = models.PositiveIntegerField(default=0)
    waived = models.PositiveIntegerField(default=0)
    sources = models.JSONField(default=list)
    class Meta:
        ordering = ['asset__product__category__name','asset__location__name','asset__code']
        constraints = [models.UniqueConstraint(fields=['event','asset'],name='unique_event_asset'),models.CheckConstraint(condition=Q(quantity__gt=0) & Q(separated__lte=F('quantity')) & Q(sent__lte=F('separated')) & Q(waived__lte=F('quantity')-F('sent')) & Q(returned__lte=F('sent')) & Q(cleared__lte=F('returned')) & Q(written_off__lte=F('sent')-F('cleared')) & Q(returned__lte=F('sent')-F('written_off')), name='consistent_line_counts')]
    @property
    def pending(self): return self.sent-self.returned-self.written_off
    @property
    def checking(self): return self.returned-self.cleared
    @property
    def to_send(self): return self.quantity-self.sent-self.waived
    def __str__(self): return f'{self.event} / {self.asset}'

class Maintenance(models.Model):
    asset = models.ForeignKey(Asset,on_delete=models.PROTECT,related_name='maintenance',verbose_name='equipamento')
    quantity = models.PositiveIntegerField('quantidade',default=1)
    kind = models.CharField('tipo',max_length=15,choices=[('preventive','Preventiva'),('corrective','Corretiva')])
    reason = models.TextField('defeito / motivo')
    provider = models.CharField('responsável / prestador',max_length=200)
    opened_at = models.DateTimeField(auto_now_add=True)
    expected = models.DateField('previsão',null=True,blank=True)
    cost = models.DecimalField('custo (R$)',max_digits=12,decimal_places=2,default=0)
    photo = models.ImageField('foto / anexo',upload_to='maintenance/%Y/%m/',blank=True)
    closed_at = models.DateTimeField(null=True,blank=True,editable=False)
    final_condition = models.TextField(blank=True,editable=False)
    class Meta:
        ordering = ['-opened_at']
        constraints = [models.CheckConstraint(condition=Q(quantity__gt=0) & Q(cost__gte=0),name='valid_maintenance')]
    def __str__(self): return f'OS {self.pk} · {self.asset}'

class Audit(models.Model):
    request_key = models.UUIDField(null=True, blank=True, unique=True, editable=False)
    at = models.DateTimeField(auto_now_add=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.PROTECT)
    action = models.CharField(max_length=60)
    event = models.ForeignKey(Event,on_delete=models.PROTECT,null=True,blank=True)
    asset = models.ForeignKey(Asset,on_delete=models.PROTECT,null=True,blank=True)
    quantity = models.IntegerField(default=0)
    detail = models.TextField()
    photo = models.ImageField(upload_to='occurrences/%Y/%m/',blank=True)
    class Meta:
        ordering = ['-at','-pk']


class CodeSequence(models.Model):
    name = models.CharField(max_length=20,primary_key=True)
    value = models.PositiveIntegerField(default=0)
