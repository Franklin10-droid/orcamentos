from django.db import models
from django.shortcuts import resolve_url as r
from django.utils.text import slugify
from django.utils.formats import number_format
from orcamentos.core.models import TimeStampedModel, Address
from .managers import EntryManager, ProposalManager
from orcamentos.utils.lists import PRIORITY, NORMAL, CATEGORY, PROP_TYPE, STATUS_LIST


class Work(Address):
    name_work = models.CharField('obra', max_length=100, unique=True)
    slug = models.SlugField('slug', blank=True)
    person = models.ForeignKey(
        'crm.Person',
        verbose_name='contato',
        related_name='work_person',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    customer = models.ForeignKey(
        'crm.Customer',
        verbose_name='cliente',
        related_name='work_customer',
        on_delete=models.CASCADE
    )

    class Meta:
        ordering = ['name_work']
        verbose_name = 'obra'
        verbose_name_plural = 'obras'

    def __str__(self):
        return self.name_work

    def get_absolute_url(self):
        if self.slug:
            return r('proposal:work_detail', slug=self.slug)

    def save(self):
        self.slug = slugify(self.name_work)
        super(Work, self).save()


class Proposal(TimeStampedModel):
    ''' Orçamento é todo orçamento com num_prop > 0 '''
    num_prop = models.PositiveIntegerField(u'número', default=0)
    priority = models.CharField(
        'prioridade',
        max_length=2,
        choices=PRIORITY,
        default=NORMAL
    )
    prop_type = models.CharField(
        u'tipo de orçamento',
        max_length=20,
        choices=PROP_TYPE,
        default='R'
    )
    num_prop_type = models.PositiveIntegerField(
        u'número da revisão',
        default=0
    )
    option_prop = models.PositiveIntegerField(
        'opção',
        null=True,
        blank=True,
        help_text='Cada orçamento pode ter opções 1, 2, 3 ...'
    )
    category = models.CharField(
        'categoria',
        max_length=4,
        choices=CATEGORY,
        default='orc'
    )
    description = models.TextField(u'descrição', blank=True)
    work = models.ForeignKey(
        'Work',
        verbose_name='obra',
        related_name='proposal_work',
        on_delete=models.CASCADE
    )
    person = models.ForeignKey(
        'crm.Person',
        verbose_name='contato',
        related_name='proposal_person',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    employee = models.ForeignKey(
        'crm.Employee',
        verbose_name=u'orçamentista',
        related_name='proposal_employee',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    seller = models.ForeignKey(
        'crm.Seller',
        verbose_name='vendedor',
        related_name='proposal_seller',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=4,
        choices=STATUS_LIST,
        default='elab'
    )
    date_conclusion = models.DateTimeField(
        u'data de conclusão',
        null=True,
        blank=True
    )
    price = models.DecimalField(
        'valor',
        max_digits=9,
        decimal_places=2,
        default=0
    )
    obs = models.TextField(u'observação', blank=True)
    created_orc = models.DateTimeField('orç. criado em', null=True, blank=True)

    objects = ProposalManager()

    class Meta:
        ordering = ['id']
        verbose_name = u'orçamento'
        verbose_name_plural = u'orçamentos'

    def __str__(self):
        # formato 001.15.0
        self.actual_year = self.created.strftime('%y')
        if self.option_prop:
            return f'{str(self.num_prop).zfill(3)}/{self.actual_year}{self.num_prop_type}-OP {self.option_prop}'
        return f'{str(self.num_prop).zfill(3)}/{self.actual_year}{self.num_prop_type}'
    codigo = property(__str__)

    def get_absolute_url(self):
        return r('proposal:proposal_detail', pk=self.pk)

    def get_price(self):
        return u"R$ %s" % number_format(self.price, 2)

    def get_customer(self):
        return self.work.customer
    cliente = property(get_customer)

    def get_customer_url(self):
        return u'/crm/customer/%s' % self.work.customer.slug

    def get_work_url(self):
        return u'/proposal/work/%s' % self.work.slug

    def get_person_url(self):
        return u'/crm/person/%s' % self.person.slug

    def get_seller(self):
        if self.seller:
            return '{} {}'.format(
                self.seller.employee.first_name,
                self.seller.employee.last_name
            )
        return ''

    def get_employee(self):
        if self.employee:
            return '{} {}'.format(self.employee.first_name, self.employee.last_name)
        return ''

    def get_address(self):
        if self.work.address:
            return '{}, {}, {} - {}'.format(
                self.work.address, self.work.district,
                self.work.city, self.work.uf
            )


class Entry(Proposal):
    ''' Entrada é todo orçamento com num_prop = 0 '''
    objects = EntryManager()

    class Meta:
        proxy = True
        ordering = ['priority', 'created']
        verbose_name = 'entrada'
        verbose_name_plural = 'entradas'

    def __str__(self):
        return str(self.work)

    def get_absolute_url(self):
        return r('proposal:entry_detail', pk=self.pk)

    def save(self):
        self.status = 'n'  # não iniciado
        super(Entry, self).save()


class Contract(TimeStampedModel):
    proposal = models.OneToOneField(
        'Proposal',
        verbose_name=u'orçamento',
        related_name='contract_proposal',
        on_delete=models.CASCADE
    )
    contractor = models.ForeignKey(
        'crm.Customer',
        verbose_name=u'contratante',
        related_name='contract_person',
        on_delete=models.CASCADE
    )
    is_canceled = models.BooleanField('cancelado', default=False)

    class Meta:
        ordering = ['proposal']
        verbose_name = u'contrato'
        verbose_name_plural = u'contratos'

    def __str__(self):
        return str(self.proposal)

    def get_absolute_url(self):
        return r('proposal:contract_detail', pk=self.pk)

    def get_price(self):
        return u"R$ %s" % number_format(self.proposal.price, 2)


class NumLastProposal(models.Model):
    num_last_prop = models.PositiveIntegerField(u'número', default=0)

    class Meta:
        verbose_name = u'número último orçamento'
        verbose_name_plural = u'número último orçamento'

    def __str__(self):
        return str(self.num_last_prop)
