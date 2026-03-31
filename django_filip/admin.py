from django.contrib import admin

from . import models


@admin.register(models.Connection)
class ConnectionAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Authentication)
class AuthenticationAdmin(admin.ModelAdmin):
    pass


@admin.register(models.TokenFlow)
class TokenFlowAdmin(admin.ModelAdmin):
    pass


@admin.register(models.ClientIdentity)
class ClientIdentityAdmin(admin.ModelAdmin):
    pass
