from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from accounts.models import Invitation, Person, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["email"]
    list_display = ["email", "is_active", "email_verified", "is_staff", "last_login"]
    search_fields = ["email"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Estado", {"fields": ("is_active", "email_verified", "is_staff", "is_superuser")}),
        ("Permisos", {"fields": ("groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )
    readonly_fields = ["last_login", "date_joined"]
    filter_horizontal = ["groups", "user_permissions"]


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ["full_name", "user", "phone", "birth_date"]
    search_fields = ["first_name", "last_name_paterno", "last_name_materno", "user__email"]


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "doctor", "status", "created_at", "expires_at", "used_at"]
    list_filter = ["status"]
    search_fields = ["email"]
    readonly_fields = ["token_hash", "created_at", "used_at"]
