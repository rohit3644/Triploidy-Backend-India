from triploidy.settings import BAM_PATH, DOMAIN
from rest_framework import serializers
from triploidy.models import *
from django.contrib.auth.models import User
import os
class DocumentStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentStore
        fields = '__all__'

def validate_domain(value):
    _, domain = value.split('@')
    if domain != DOMAIN:
        raise Exception('Invalid user')

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'first_name', 'last_name')
        extra_kwargs = {'password': {'write_only': True}}
    
    def create(self, validated_data):
        validate_domain(validated_data['username'])
        validate_domain(validated_data['email'])
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            is_active=False
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class UploadSampleRequestSerializer(serializers.Serializer):
    run_id = serializers.CharField(required=True)
    file = serializers.FileField(required=True)
    bam_directory_path = serializers.CharField(required=True)

    def validate_bam_directory_path(self, value):
        """
        Validate that the provided server path exists.
        """
        for path in BAM_PATH:
            temp_value = os.path.join(path, value)
            if os.path.exists(temp_value) and os.path.isdir(temp_value):
                # Check if the directory contains .bam files
                with os.scandir(temp_value) as entries:
                    bam_files = any(entry.is_file() and entry.name.lower().endswith('.bam') for entry in entries)
                    
                if bam_files:
                    # If .bam files exist, return the original value
                    return value

        # If no valid directory with .bam files is found, raise an exception
        raise Exception("Provided directory path does not exist or does not contain any .bam files.")

class ParentalUploadSampleRequestSerializer(serializers.Serializer):
    run_id = serializers.CharField(required=True)
    file = serializers.FileField(required=True)
    bam_directory_path = serializers.CharField(required=True)

    # def validate_bam_directory_path(self, value):
    #     """
    #     Validate that the provided server path exists.
    #     """
    #     for temp_value in ['/mnt/India/bioinfo/GUI_application/Parental_Identification/sample']:
    #         if os.path.exists(temp_value) and os.path.isdir(temp_value):
    #             # Check if the directory contains .bam files
    #             with os.scandir(temp_value) as entries:
    #                 bam_files = any(entry.is_file() and entry.name.lower().endswith('.bam') for entry in entries)
                    
    #             if bam_files:
    #                 # If .bam files exist, return the original value
    #                 return value

    #     # If no valid directory with .bam files is found, raise an exception
    #     raise Exception("Provided directory path does not exist or does not contain any .bam files.")


class SampleHistorySerializer(serializers.ModelSerializer):
    input_file_url = serializers.SerializerMethodField()

    class Meta:
        model = SampleHistory
        fields = '__all__'

    def get_input_file_url(self, obj):
        status_handling_query = StatusHandling.objects.filter(run_id=obj.run_id)
        latest_status_handling = status_handling_query.order_by('-id').first()

        if latest_status_handling:
            return latest_status_handling.file_url
        else:
            return ''

class ParentalSampleHistorySerializer(serializers.ModelSerializer):
    input_file_url = serializers.SerializerMethodField()

    class Meta:
        model = ParentalSampleHistory
        fields = '__all__'

    def get_input_file_url(self, obj):
        status_handling_query = ParentalStatusHandling.objects.filter(run_id=obj.run_id)
        latest_status_handling = status_handling_query.order_by('-id').first()

        if latest_status_handling:
            return latest_status_handling.file_url
        else:
            return ''

class ParentalPloidyUploadSampleRequestSerializer(serializers.Serializer):
    run_id = serializers.CharField(required=True)
    file = serializers.FileField(required=True)
    bam_directory_path = serializers.CharField(required=True)


class ParentalPloidySampleHistorySerializer(serializers.ModelSerializer):
    input_file_url = serializers.SerializerMethodField()

    class Meta:
        model = ParentalPloidySampleHistory
        fields = '__all__'

    def get_input_file_url(self, obj):
        status_handling_query = ParentalPloidyStatusHandling.objects.filter(run_id=obj.run_id)
        latest_status_handling = status_handling_query.order_by('-id').first()

        if latest_status_handling:
            return latest_status_handling.file_url
        else:
            return ''

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(required=False)


class PloidySerializer(serializers.ModelSerializer):
    class Meta:
        model = Ploidy
        fields = '__all__'