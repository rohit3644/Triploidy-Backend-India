from django.contrib import admin
from triploidy.models import *

@admin.register(DocumentStore)
class DocumentStoreAdmin(admin.ModelAdmin):
    list_display = ["name","value"]
    search_fields = ["name"]

@admin.register(SampleHistory)
class SampleHistoryAdmin(admin.ModelAdmin):
    list_display = ['run_id','accession_number','is_complete','created_at','updated_at']
    search_fields = ['is_complete']

@admin.register(StatusHandling)
class StatusHandlingAdmin(admin.ModelAdmin):
    list_display = ["run_id", "message"]
    
    search_fields = ["run_id"]


@admin.register(ParentalSampleHistory)
class ParentalSampleHistoryAdmin(admin.ModelAdmin):
    list_display = ['run_id','accession_number','is_complete','created_at','updated_at']
    search_fields = ['is_complete']

@admin.register(ParentalStatusHandling)
class ParentalStatusHandlingAdmin(admin.ModelAdmin):
    list_display = ["run_id", "message"]
    
    search_fields = ["run_id"]

@admin.register(ParentalPloidySampleHistory)
class ParentalPloidySampleHistoryAdmin(admin.ModelAdmin):
    list_display = ['run_id','accession_number','is_complete','created_at','updated_at']
    search_fields = ['is_complete']

@admin.register(ParentalPloidyStatusHandling)
class ParentalPloidyStatusHandlingAdmin(admin.ModelAdmin):
    list_display = ["run_id", "message"]
    
    search_fields = ["run_id"]


@admin.register(Ploidy)
class PloidyAdmin(admin.ModelAdmin):
    list_display = [
        "barcode",
        "pn_status",
        "triploid",
        "log2_haploid_1",
        "haploid_1",
        "haploid_2"
    ]
    
    search_fields = ["barcode"]

