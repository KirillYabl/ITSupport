from django.contrib import admin

from . import models as m


@admin.register(m.Client)
class ClientAdmin(admin.ModelAdmin):
    pass


@admin.register(m.Contractor)
class ContractorAdmin(admin.ModelAdmin):
    pass


@admin.register(m.Manager)
class ManagerAdmin(admin.ModelAdmin):
    pass


@admin.register(m.Owner)
class OwnerAdmin(admin.ModelAdmin):
    pass


@admin.register(m.Tariff)
class TariffAdmin(admin.ModelAdmin):
    pass


@admin.register(m.Order)
class OrderAdmin(admin.ModelAdmin):
    pass


@admin.register(m.AssignedContractor)
class AssignedContractorAdmin(admin.ModelAdmin):
    pass


@admin.register(m.SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    pass
