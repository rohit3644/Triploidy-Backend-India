from triploidy.settings import BASE_URL, EMAIL_HOST_USER, FRONTEND_EMAIL_VERIFY_URL, FRONTEND_PASSWORD_RESET_URL
from triploidy.utils import generic_send_email, get_file_url, kill_running_process, process_upload_sample, process_upload_sample_parental, process_upload_sample_parental_ploidy, response
from rest_framework.decorators import api_view
from triploidy.serializers import *
import pandas as pd
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import authenticate, login, logout
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
import os
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core.mail import send_mail
from threading import Thread
from django.db.models import *

@api_view(['POST','GET'])
@permission_classes([IsAuthenticated])
def documents(request):
    try:
        if request.method == 'POST':
            name = request.data.get('name')
            if DocumentStore.objects.filter(name=name).exists():
                return response(None,"A record with the same name already exists.",False,400)
            serializer = DocumentStoreSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return response(serializer.data,"Success",True,201)
            return response("Request Failed",str(e),False,400)
        elif request.method == "GET":
            name = request.query_params.get('name', None)
            if name is not None:
                documents = DocumentStore.objects.filter(name=name)
            else:
                return response(None,"name param is required.",False,400)
            serializer = DocumentStoreSerializer(documents,many=True)
            return response(serializer.data,"Success",True,200)
    except Exception as e:
        return response("Request Failed",str(e),False,400)


@api_view(['POST'])
def login_view(request):
    try:
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(username=email, password=password)

        if user is not None:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            if not created:
                token.delete()
                token = Token.objects.create(user=user)
            return response({'token': token.key,"first_name":user.first_name,"last_name":user.last_name, "username":user.username},"Success",True,200)
        else:
            return response('Invalid credentials',"Request Failed",False,401)
    except Exception as e:
        return response("Request Failed",str(e),False,400)


@api_view(['POST'])
def signup_view(request):
    try:
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            user = User.objects.get(email=serializer.data['email'])
            # Generate reset token
            uid = urlsafe_base64_encode(force_bytes(user.username))
            token = default_token_generator.make_token(user)

            # Build reset link
            verify_link = FRONTEND_EMAIL_VERIFY_URL.format(uid=uid,token=token,email=serializer.data['email'])

            generic_send_email(
                'Email Verification',
                f'Click the following link to verify your email: {verify_link}',
                [serializer.data['email']],
            )
            return response(serializer.data,"A verification link has been sent to your email",True,200)
        return response(serializer.errors,"Request Failed",False,400)
    except Exception as e:
        return response("Request Failed",str(e),False,400)

@api_view(['POST'])
def signup_confirm(request,uid,token):
    try:
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise Exception('User not found')
            
            local_uid = urlsafe_base64_encode(force_bytes(user.username))
            if local_uid != uid:
                raise Exception('Invalid verify uid')

            # Check if the provided password reset token is valid
            if not default_token_generator.check_token(user, token):
                raise Exception('Invalid verify token')

            user.is_active = True
            user.save()
            return response({},"Email verified successfully",True,200)

        raise Exception('Invalid data')
    except Exception as e:
        return response("Request Failed",str(e),False,400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    if request.user.is_authenticated:
        Token.objects.filter(user=request.user.id).delete()
        logout(request)
        return response({},"Success",True,200)
    else:
        return response('User is not authenticated',"Request Failed",False,401)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_view(request):
    try:
        serializer = UploadSampleRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return response(serializer.errors,"Request Failed",False,400)
        excel_file = serializer.validated_data.get('file')
        try:
            df = pd.read_excel(excel_file)
        except pd.errors.EmptyDataError:
            try:
                df = pd.read_csv(excel_file)
            except pd.errors.ParserError:
                raise Exception('Invalid file format')
        file_name = excel_file.name
        file_path = f'media/processed/{serializer.validated_data.get("bam_directory_path")}/{file_name}'
        parent_directory = os.path.dirname(file_path)
        if not os.path.exists(parent_directory):
            os.makedirs(parent_directory)
        with open(file_path, 'wb') as destination:
            for chunk in excel_file.chunks():
                destination.write(chunk)
        file_url = os.path.join(BASE_URL,file_path)
        df.fillna('-')
        data_list = df.to_dict(orient='records')
        process_upload_sample.delay(serializer.data,file_url, data_list)

        return response({"run_id":serializer.validated_data.get('bam_directory_path')},"Success",True,200)
    except Exception as e:
        return response("Request Failed",str(e),False,400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search(request):
    try:
        run_id = request.GET.get('run_id')
        accession_number = request.GET.get('accession_number')
        date = request.GET.get('date')
        is_output = request.GET.get('is_output')
        if is_output in [True,"True","true","1",1]:
            is_output = True
        else:
            is_output = False
        if not is_output:
            filters = {}
            if run_id:
                filters['run_id'] = run_id
            if accession_number:
                filters['accession_number'] = accession_number
            if date:
                filters['created_at__date'] = date
            if not filters:
                raise Exception('Please select a filter')
            data = SampleHistory.objects.annotate(
                input_file_url=Subquery(StatusHandling.objects.filter(run_id=OuterRef('run_id')).values('file_url').order_by('-id')[:1],output_field=models.CharField()),
            ).filter(**filters).values().order_by('-pk')
            if data:
                for rec in data:
                    rec['log_file'] = get_file_url('/app/media/output',rec['run_id'],file_extension='log')
                    rec['output_file'] = get_file_url(f'/app/media/processed/{rec["run_id"]}',f"{rec['run_id']}ploidy_final_report",file_extension='xlsx')
                    rec['intermediate_file_1'] = get_file_url(f'/app/media/processed/{rec["run_id"]}',f'{rec["run_id"]}graph',file_extension='png')
                    rec['intermediate_file_2'] = get_file_url(f'/app/media/processed/{rec["run_id"]}',rec["run_id"],file_extension='csv')
                    rec['triploid_graph'] = get_file_url(f'/app/media/processed/{rec["run_id"]}',f'{rec["run_id"]}tri_graph',file_extension='png')
                    rec['haploid1_graph'] = get_file_url(f'/app/media/processed/{rec["run_id"]}',f'{rec["run_id"]}hap1_graph',file_extension='png')
                    rec['haploid2_graph'] = get_file_url(f'/app/media/processed/{rec["run_id"]}',f'{rec["run_id"]}hap2_graph',file_extension='png')
                return response(data,"Success",True,200)
        else:
            file_link = get_file_url('/app/media/output',run_id,file_extension='log')
            if file_link:
                res = f"File is processing, please use this url to check logs - <a target='_blank' href='{file_link}'>Output Log File</a>"
                return response(res,"Success",True,200)
            else:
                status = StatusHandling.objects.filter(run_id=run_id).last()
                if status:
                    return response(status.message,"Success",True,200)
        return response('No record found',"Success",True,200)
    except Exception as e:
        return response("Request Failed",str(e),False,400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def history(request):
    try:
        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 100  # Adjust the page size as needed

        # Queryset
        queryset = SampleHistory.objects.all().order_by('-pk')

        # Paginate queryset
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = SampleHistorySerializer(result_page, many=True)

        for rec in serializer.data:
            rec['log_file'] = get_file_url('/app/media/output',rec['run_id'],file_extension='log')
            rec['output_file'] = get_file_url(f'/app/media/processed/{rec["run_id"]}',f"{rec['run_id']}ploidy_final_report",file_extension='xlsx')
            rec['intermediate_file_1'] = get_file_url(f'/app/media/processed/{rec["run_id"]}',f'{rec["run_id"]}graph',file_extension='png')
            rec['intermediate_file_2'] = get_file_url(f'/app/media/processed/{rec["run_id"]}',rec["run_id"],file_extension='csv')
            rec['triploid_graph'] = get_file_url(f'/app/media/processed/{rec["run_id"]}',f'{rec["run_id"]}tri_graph',file_extension='png')
            rec['haploid1_graph'] = get_file_url(f'/app/media/processed/{rec["run_id"]}',f'{rec["run_id"]}hap1_graph',file_extension='png')
            rec['haploid2_graph'] = get_file_url(f'/app/media/processed/{rec["run_id"]}',f'{rec["run_id"]}hap2_graph',file_extension='png')

        results = {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data
        }

        return response(results,"Success",True,200)
    except Exception as e:
        return response("Request Failed",str(e),False,400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_media(request):
    try:
        file = request.FILES.get('file')
        file_name = file.name
        file_path = f'media/{file_name}'
        with open(file_path, 'wb') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        file_url = os.path.join(BASE_URL,file_path)
        return response({"file_url":file_url},"Success",True,200)
    except Exception as e:
        return response("Request Failed",str(e),False,400)
    

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_sample_history(request, run_id):
    try:
        # Assuming run_id is a unique identifier for the records you want to delete
        sample_histories = SampleHistory.objects.filter(run_id=run_id)
        queryset = StatusHandling.objects.filter(run_id=run_id)

        if not sample_histories.exists() and not queryset.exists():
            return response("No records found for the specified run_id","Request Failed",False,404)

        # Delete the records
        if sample_histories.exists():
            sample_histories.delete()
        if queryset.exists():
            queryset.delete()
        return response({},"Records deleted successfully",True,204)

    except Exception as e:
        return response("Request Failed",str(e),False,400)
    

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_list_ploidy(request, id):
    try:
        # Assuming run_id is a unique identifier for the records you want to delete
        ploidys = Ploidy.objects.filter(id=id)

        if not ploidys.exists():
            return response("No records found for the specified id","Request Failed",False,404)

        # Delete the records
        if ploidys.exists():
            ploidys.delete()

        return response({},"Records deleted successfully",True,204)

    except Exception as e:
        return response("Request Failed",str(e),False,400)


@api_view(['POST'])
def password_reset(request):
    try:
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise Exception('User not found')

            # Generate reset token
            uid = urlsafe_base64_encode(force_bytes(user.username))
            token = default_token_generator.make_token(user)

            # Build reset link
            reset_link = FRONTEND_PASSWORD_RESET_URL.format(uid=uid,token=token,email=email)

            # Send reset email
            send_mail(
                'Password Reset',
                f'Click the following link to reset your password: {reset_link}',
                EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )

            return response({},"Password reset email sent successfully",True,200)

        raise Exception('Invalid data')
    except Exception as e:
        return response("Request Failed",str(e),False,400)


@api_view(['POST'])
def password_reset_confirm(request,uid,token):
    try:
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise Exception('User not found')

            local_uid = urlsafe_base64_encode(force_bytes(user.username))
            if local_uid != uid:
                raise Exception('Invalid verify uid')

            # Check if the provided password reset token is valid
            if not default_token_generator.check_token(user, token):
                raise Exception('Invalid reset token')

            # Set the new password
            if password:
                user.set_password(password)
                user.save()
                return response({},"Password reset successfully",True,200)
            else:
                raise Exception('Invalid password format')

        raise Exception('Invalid data')
    except Exception as e:
        return response("Request Failed",str(e),False,400)

####################### PARENTAL APIS #########################################################

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def parental_upload_view(request):
    try:
        serializer = ParentalUploadSampleRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return response(serializer.errors,"Request Failed",False,400)
        excel_file = serializer.validated_data.get('file')
        try:
            df = pd.read_excel(excel_file)
        except pd.errors.EmptyDataError:
            try:
                df = pd.read_csv(excel_file)
            except pd.errors.ParserError:
                raise Exception('Invalid file format')
        file_name = excel_file.name
        file_path = f'media/processed/{serializer.validated_data.get("bam_directory_path")}/{file_name}'
        parent_directory = os.path.dirname(file_path)
        if not os.path.exists(parent_directory):
            os.makedirs(parent_directory)
        with open(file_path, 'wb') as destination:
            for chunk in excel_file.chunks():
                destination.write(chunk)
        file_url = os.path.join(BASE_URL,file_path)
        df.fillna('-')
        data_list = df.to_dict(orient='records')
        process_upload_sample_parental.delay(serializer.data,file_url, data_list)

        return response({"run_id":serializer.validated_data.get('bam_directory_path')},"Success",True,200)
    except Exception as e:
        return response("Request Failed",str(e),False,400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def parental_search(request):
    try:
        run_id = request.GET.get('run_id')
        accession_number = request.GET.get('accession_number')
        date = request.GET.get('date')
        is_output = request.GET.get('is_output')
        if is_output in [True,"True","true","1",1]:
            is_output = True
        else:
            is_output = False
        if not is_output:
            filters = {}
            if run_id:
                filters['run_id'] = run_id
            if accession_number:
                filters['accession_number'] = accession_number
            if date:
                filters['created_at__date'] = date
            if not filters:
                raise Exception('Please select a filter')
            data = ParentalSampleHistory.objects.annotate(
                input_file_url=Subquery(ParentalStatusHandling.objects.filter(run_id=OuterRef('run_id')).values('file_url').order_by('-id')[:1],output_field=models.CharField()),
            ).filter(**filters).values().order_by('-pk')
            if data:
                for rec in data:
                    rec['log_file'] = get_file_url('/app/media/parental_identification/output',rec['run_id'],file_extension='log')
                    rec['output_file'] = get_file_url(f'/app/media/parental_identification/processed/{rec["run_id"]}',rec['run_id'], file_extension='tsv')
                    rec['intermediate_file_1'] = get_file_url(f'/app/media/parental_identification/processed/{rec["run_id"]}',f'{rec["run_id"]}_matching',file_extension='tsv')
                    rec['intermediate_file_2'] = get_file_url(f'/app/media/parental_identification/processed/{rec["run_id"]}/{rec["accession_number"]}/vcf',f'{rec["accession_number"]}_CON1_AF',file_extension='bed')
                return response(data,"Success",True,200)
        else:
            file_link = get_file_url('/app/media/parental_identification/output',run_id,file_extension='log')
            if file_link:
                res = f"File is processing, please use this url to check logs - <a target='_blank' href='{file_link}'>Output Log File</a>"
                return response(res,"Success",True,200)
            else:
                status = ParentalStatusHandling.objects.filter(run_id=run_id).last()
                if status:
                    return response(status.message,"Success",True,200)
        return response('No record found',"Success",True,200)
    except Exception as e:
        return response("Request Failed",str(e),False,400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def killing_process(request):
    try:
        kill_running_process.delay()
        return response({},"Success",True,200)
    except Exception as e:
        return response("Request Failed",f"{str(e)}({e.__traceback__.tb_lineno})",False,400)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def parental_history(request):
    try:
        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 100  # Adjust the page size as needed

        # Queryset
        queryset = ParentalSampleHistory.objects.all().order_by('-pk')

        # Paginate queryset
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = ParentalSampleHistorySerializer(result_page, many=True)

        for rec in serializer.data:
            rec['log_file'] = get_file_url('/app/media/parental_identification/output',rec['run_id'],file_extension='log')
            rec['output_file'] = get_file_url(f'/app/media/parental_identification/processed/{rec["run_id"]}',rec['run_id'], file_extension='tsv')
            rec['intermediate_file_1'] = get_file_url(f'/app/media/parental_identification/processed/{rec["run_id"]}',f'{rec["run_id"]}_matching',file_extension='tsv')
            rec['intermediate_file_2'] = get_file_url(f'/app/media/parental_identification/processed/{rec["run_id"]}/{rec["accession_number"]}/vcf',f'{rec["accession_number"]}_CON1_AF',file_extension='bed')

        results = {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data
        }

        return response(results,"Success",True,200)
    except Exception as e:
        return response("Request Failed",str(e),False,400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def parental_delete_sample_history(request, run_id):
    try:
        # Assuming run_id is a unique identifier for the records you want to delete
        sample_histories = ParentalSampleHistory.objects.filter(run_id=run_id)
        queryset = ParentalStatusHandling.objects.filter(run_id=run_id)

        if not sample_histories.exists() and not queryset.exists():
            return response("No records found for the specified run_id","Request Failed",False,404)

        # Delete the records
        if sample_histories.exists():
            sample_histories.delete()
        if queryset.exists():
            queryset.delete()
        return response({},"Records deleted successfully",True,204)

    except Exception as e:
        return response("Request Failed",str(e),False,400)
    


####################### PARENTAL PLOIDY APIS #########################################################

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def parental_ploidy_upload_view(request):
    try:
        serializer = ParentalPloidyUploadSampleRequestSerializer(data=request.data)

        if not serializer.is_valid():
            return response(serializer.errors,"Request Failed",False,400)
        excel_file = serializer.validated_data.get('file')
        try:
            df = pd.read_excel(excel_file)
        except pd.errors.EmptyDataError:
            try:
                df = pd.read_csv(excel_file)
            except pd.errors.ParserError:
                raise Exception('Invalid file format')
        file_name = excel_file.name
        file_path = f'media/processed/{serializer.validated_data.get("bam_directory_path")}/{file_name}'
        parent_directory = os.path.dirname(file_path)
        if not os.path.exists(parent_directory):
            os.makedirs(parent_directory)
        with open(file_path, 'wb') as destination:
            for chunk in excel_file.chunks():
                destination.write(chunk)
        file_url = os.path.join(BASE_URL,file_path)
        df.fillna('-')
        data_list = df.to_dict(orient='records')
        process_upload_sample_parental_ploidy.delay(serializer.data,file_url, data_list)

        return response({"run_id":serializer.validated_data.get('bam_directory_path')},"Success",True,200)
    except Exception as e:
        return response("Request Failed",str(e),False,400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def parental_ploidy_search(request):
    try:
        run_id = request.GET.get('run_id')
        accession_number = request.GET.get('accession_number')
        date = request.GET.get('date')
        is_output = request.GET.get('is_output')
        if is_output in [True,"True","true","1",1]:
            is_output = True
        else:
            is_output = False
        if not is_output:
            filters = {}
            if run_id:
                filters['run_id'] = run_id
            if accession_number:
                filters['accession_number'] = accession_number
            if date:
                filters['created_at__date'] = date
            if not filters:
                raise Exception('Please select a filter')
            data = ParentalPloidySampleHistory.objects.annotate(
                input_file_url=Subquery(ParentalPloidyStatusHandling.objects.filter(run_id=OuterRef('run_id')).values('file_url').order_by('-id')[:1],output_field=models.CharField()),
            ).filter(**filters).values().order_by('-pk')
            if data:
                for rec in data:
                    rec['log_file'] = get_file_url('/app/media/parental_ploidy/output',rec['run_id'],file_extension='log')
                    rec['output_file'] = get_file_url(f'/app/media/parental_ploidy/processed/{rec["run_id"]}',f"{rec['run_id']}_p+t_ploidy_final_report",file_extension='csv')
                    rec['intermediate_file_1'] = get_file_url(f'/app/media/parental_ploidy/processed/{rec["run_id"]}',f'{rec["run_id"]}',file_extension='csv')
                    rec['intermediate_file_2'] = get_file_url(f'/app/media/parental_ploidy/processed/{rec["run_id"]}',f'{rec["run_id"]}_ploidy_paternity',file_extension='csv')
                    rec['triploid_graph'] = get_file_url(f'/app/media/parental_ploidy/processed/{rec["run_id"]}',f'{rec["run_id"]}tri_graph',file_extension='png')
                    rec['haploid1_graph'] = get_file_url(f'/app/media/parental_ploidy/processed/{rec["run_id"]}',f'{rec["run_id"]}hap1_graph',file_extension='png')
                    rec['haploid2_graph'] = get_file_url(f'/app/media/parental_ploidy/processed/{rec["run_id"]}',f'{rec["run_id"]}hap2_graph',file_extension='png')
                return response(data,"Success",True,200)
        else:
            file_link = get_file_url('/app/media/parental_ploidy/output',run_id,file_extension='log')
            if file_link:
                res = f"File is processing, please use this url to check logs - <a target='_blank' href='{file_link}'>Output Log File</a>"
                return response(res,"Success",True,200)
            else:
                status = ParentalPloidyStatusHandling.objects.filter(run_id=run_id).last()
                if status:
                    return response(status.message,"Success",True,200)
        return response('No record found',"Success",True,200)
    except Exception as e:
        return response("Request Failed",str(e),False,400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def parental_ploidy_history(request):
    try:
        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 100  # Adjust the page size as needed

        # Queryset
        queryset = ParentalPloidySampleHistory.objects.all().order_by('-pk')

        # Paginate queryset
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = ParentalPloidySampleHistorySerializer(result_page, many=True)

        for rec in serializer.data:
            rec['log_file'] = get_file_url('/app/media/parental_ploidy/output',rec['run_id'],file_extension='log')
            rec['output_file'] = get_file_url(f'/app/media/parental_ploidy/processed/{rec["run_id"]}',f"{rec['run_id']}_p+t_ploidy_final_report",file_extension='csv')
            rec['intermediate_file_1'] = get_file_url(f'/app/media/parental_ploidy/processed/{rec["run_id"]}',f'{rec["run_id"]}',file_extension='csv')
            rec['intermediate_file_2'] = get_file_url(f'/app/media/parental_ploidy/processed/{rec["run_id"]}',f'{rec["run_id"]}_ploidy_paternity',file_extension='csv')
            rec['triploid_graph'] = get_file_url(f'/app/media/parental_ploidy/processed/{rec["run_id"]}',f'{rec["run_id"]}tri_graph',file_extension='png')
            rec['haploid1_graph'] = get_file_url(f'/app/media/parental_ploidy/processed/{rec["run_id"]}',f'{rec["run_id"]}hap1_graph',file_extension='png')
            rec['haploid2_graph'] = get_file_url(f'/app/media/parental_ploidy/processed/{rec["run_id"]}',f'{rec["run_id"]}hap2_graph',file_extension='png')

        results = {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data
        }

        return response(results,"Success",True,200)
    except Exception as e:
        return response("Request Failed",str(e),False,400)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def parental_ploidy_delete_sample_history(request, run_id):
    try:
        # Assuming run_id is a unique identifier for the records you want to delete
        sample_histories = ParentalPloidySampleHistory.objects.filter(run_id=run_id)
        queryset = ParentalPloidyStatusHandling.objects.filter(run_id=run_id)

        if not sample_histories.exists() and not queryset.exists():
            return response("No records found for the specified run_id","Request Failed",False,404)

        # Delete the records
        if sample_histories.exists():
            sample_histories.delete()
        if queryset.exists():
            queryset.delete()
        return response({},"Records deleted successfully",True,204)

    except Exception as e:
        return response("Request Failed",str(e),False,400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_ploidy(request):
    try:
        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 1000  # Adjust the page size as needed

        # Queryset
        queryset = Ploidy.objects.all().order_by('-pk')

        # Paginate queryset
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = PloidySerializer(result_page, many=True)

        results = {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data
        }

        return response(results,"Success",True,200)
    except Exception as e:
        return response("Request Failed",str(e),False,400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_ploidy(request):
    try:
        # Pagination
        paginator = PageNumberPagination()
        paginator.page_size = 100  # Adjust the page size as needed

        request_data = request.query_params.dict()

        filters = {}

        if request_data.get('accession_number'):
            filters['barcode'] = request_data.get('accession_number')
        
        if request_data.get('pn_status'):
            filters['pn_status'] = request_data.get('pn_status')
        
        sort = request_data.get('sort','-pk')
        

        # Queryset
        queryset = Ploidy.objects.filter(**filters).order_by(sort)

        # Paginate queryset
        result_page = paginator.paginate_queryset(queryset, request)
        serializer = PloidySerializer(result_page, many=True)

        results = {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data
        }

        return response(results,"Success",True,200)
    except Exception as e:
        return response("Request Failed",str(e),False,400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_ploidy(request):
    if 'file' not in request.FILES:
        return response("No file provided",'Please upload an excel file',False,400)
    
    file = request.FILES['file']
    
    try:
        df = pd.read_excel(file)
    except Exception as e:
        return response("File not valid",f"Error reading Excel file: {str(e)}",False,400)
    
    barcodes = df['Accession Number'].tolist()
    existing_barcodes = set(Ploidy.objects.filter(barcode__in=barcodes).values_list('barcode', flat=True))
    
    new_records = []
    errors = []

    for _, row in df.iterrows():
        barcode = row['Accession Number']
        if barcode in existing_barcodes:
            errors.append(f"Barcode {barcode} already exists.")
        else:
            ploidy_data = Ploidy(
                barcode=barcode,
                pn_status=row.get('PN_Status', ''),
                triploid=row.get('Triploid - AF(33+66) / AF(33+50+66)', 0),
                haploid_1=row.get('Haploid -1 AF(33+50+66+100) / AF(33+50+66)', 0),
                log2_haploid_1=row.get('log2 Haploid -1 AF(33+50+66+100) / AF(33+50+66)', 0),
                haploid_2=row.get('Haploid -2 (AF100) / ((AF33+AF50+AF66+AF100*2)/2', 0)
            )
            new_records.append(ploidy_data)
    
    if errors:
        return response(f"Duplicate barcodes: {errors}","Duplicate barcodes found! Please try to rename the barcodes",False,400)
    
    if new_records:
        Ploidy.objects.bulk_create(new_records)

    return response({"created": len(new_records)},"All records processed successfully",True,200)