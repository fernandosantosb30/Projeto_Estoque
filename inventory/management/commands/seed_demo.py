from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from inventory.models import *
from inventory import services as s
class Command(BaseCommand):
    help='Cria dados fictícios e três reservas simultâneas; exige banco sem eventos.'
    def add_arguments(self,parser): parser.add_argument('--username',required=True)
    @s.serialized
    def handle(self,*args,**options):
        user=get_user_model().objects.get(username=options['username'])
        if Event.objects.exists(): raise CommandError('Demonstração só pode ser carregada em banco sem eventos.')
        call_command('setup_roles')
        sound=Category.objects.create(name='Sonorização')
        stage=Category.objects.create(name='Estruturas de palco')
        accessories=Category.objects.create(name='Acessórios e consumo')
        loc=Location.objects.create(name='Depósito A · Corredor 01 · Prateleira 02')
        speakers=Product.objects.create(name='Caixa ativa 12 polegadas',category=sound,kind='unit',brand='Demonstração',model='Ativa 12')
        cables=Product.objects.create(name='Cabo XLR 10 metros',category=accessories,kind='bulk')
        truss=Product.objects.create(name='Treliça Q30 · 2 metros',category=stage,kind='unit')
        tape=Product.objects.create(name='Fita gaffer preta · rolo',category=accessories,kind='supply',minimum=10)
        for i in range(1,7):
            a=Asset.objects.create(code=f'CX-{i:03}',product=speakers,location=loc,serial=f'DEMO-CX-{i}')
            s.adjust(user,a.pk,1,'Inventário inicial fictício validado para demonstração')
        for i in range(1,4):
            a=Asset.objects.create(code=f'TR-{i:03}',product=truss,location=loc)
            s.adjust(user,a.pk,1,'Inventário inicial fictício')
        cable=Asset.objects.create(code='XLR-10M',product=cables,location=loc)
        s.adjust(user,cable.pk,60,'Inventário inicial fictício')
        consumable=Asset.objects.create(code='GAFFER',product=tape,location=loc)
        s.adjust(user,consumable.pk,8,'Inventário inicial fictício')
        kit=Kit.objects.create(name='Som para palestra',notes='Duas caixas e seis cabos XLR.')
        KitComponent.objects.create(kit=kit,product=speakers,quantity=2)
        KitComponent.objects.create(kit=kit,product=cables,quantity=6)
        t=timezone.now().replace(hour=10,minute=0,second=0,microsecond=0)+timedelta(days=2)
        for index,name in enumerate(['Congresso Conexões','Festival da Praça','Encontro Horizonte']):
            client=Client.objects.create(name=['Conexões Eventos','Instituto Praça Viva','Horizonte Produções'][index],contact='Contato fictício')
            ev=Event.objects.create(name=name,client=client,place=['Centro de convenções','Praça central','Espaço Horizonte'][index],manager=user,withdrawal=t,assembly=t+timedelta(hours=2),start=t+timedelta(hours=5),end=t+timedelta(hours=12),expected_return=t+timedelta(days=1),release=t+timedelta(days=1,hours=2))
            s.audit(user,'Evento criado',ev,detail='Demonstração fictícia')
            s.add_kit(user,ev.pk,kit.pk)
            s.add_line(user,ev.pk,consumable.pk,2)
            s.transition(user,ev.pk,'reserve')
        self.stdout.write(self.style.SUCCESS('Demonstração criada: três eventos simultâneos, sem unidades duplicadas.'))
