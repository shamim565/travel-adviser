from django.db import models
from django.contrib import admin


class Division(models.Model):
    name = models.CharField(max_length=100)
    bn_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "bn_name",
        "created_at",
        "updated_at",
    )
    search_fields = ("name", "bn_name")
