from django.db import models

class DocumentStore(models.Model):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class SampleHistory(models.Model):
    run_id = models.CharField(max_length=50)
    accession_number = models.CharField(max_length=50)
    is_complete = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class StatusHandling(models.Model):
    run_id = models.CharField(max_length=255, db_index=True)
    file_url = models.URLField()
    message = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.run_id

    class Meta:
        indexes = [
            models.Index(fields=['run_id'])
        ]


class ParentalSampleHistory(models.Model):
    run_id = models.CharField(max_length=50)
    accession_number = models.CharField(max_length=50)
    is_complete = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ParentalStatusHandling(models.Model):
    run_id = models.CharField(max_length=255, db_index=True)
    file_url = models.URLField()
    message = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.run_id

    class Meta:
        indexes = [
            models.Index(fields=['run_id'])
        ]

class ParentalPloidySampleHistory(models.Model):
    run_id = models.CharField(max_length=50)
    accession_number = models.CharField(max_length=50)
    is_complete = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ParentalPloidyStatusHandling(models.Model):
    run_id = models.CharField(max_length=255, db_index=True)
    file_url = models.URLField()
    message = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.run_id

    class Meta:
        indexes = [
            models.Index(fields=['run_id'])
        ]

class Ploidy(models.Model):
    barcode = models.CharField(max_length=255, db_index=True)
    pn_status = models.CharField(max_length=10)
    triploid = models.FloatField(default=0)
    haploid_1 = models.FloatField(default=0)
    log2_haploid_1 = models.FloatField(default=0)
    haploid_2 = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['barcode'])
        ]