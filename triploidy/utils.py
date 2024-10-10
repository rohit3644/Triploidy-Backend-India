from triploidy.models import ParentalPloidySampleHistory, ParentalPloidyStatusHandling, ParentalSampleHistory, ParentalStatusHandling, SampleHistory, StatusHandling
from triploidy.settings import BASE_URL, EMAIL_HOST_USER
from rest_framework.response import Response
import os
from django.core.mail import send_mail
from triploidy.celery import app
import asyncio, shutil

def response(data={},message="",status=True,code=200):
    response_data = {"data":data,"message":message,"status":status}
    return Response(response_data, status=code)


async def read_output(stream, prefix, log_file):
    while True:
        line = await stream.readline()
        if not line:
            break
        log_file.write(f"{prefix}: {line.decode()}")
        log_file.flush()
        # print(f"{prefix}: {line.decode()}", end='', flush=True)

async def run_command(command,log_file_path):
    # Open a log file to write stdout and stderr
    with open(log_file_path, 'w+') as log_file:
        # Start the subprocess
        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

        # Start reading stdout and stderr in separate tasks
        stdout_task = asyncio.create_task(read_output(process.stdout, "STDOUT", log_file))
        stderr_task = asyncio.create_task(read_output(process.stderr, "STDERR", log_file))

        # Wait for the subprocess to finish
        return_code = await process.wait()

        # Wait for the stdout and stderr tasks to finish
        await asyncio.gather(stdout_task, stderr_task)

    # Print the return code
    return return_code

@app.task
def kill_running_process():
    try:
        command = ['bash','/home/progenesis/mnt/India/bioinfo/GUI_application/triploidy/new_pipeline/kill_check/kill.sh']
        log_file_path = f'/app/media/output/process_kill.log'
        return_code = asyncio.run(run_command(command,log_file_path))

        if return_code == 0:
            print("Command Successful!")
        else:
            print("Command Failed!")
    except Exception as e:
        print(f"Command Failed with exception, {str(e)}({e.__traceback__.tb_lineno})")


@app.task
def process_upload_sample(serializer,file_url, data_list):
    try:
        StatusHandling.objects.create(run_id=serializer.get('bam_directory_path'),message='Processing',file_url=file_url)
        for rec in data_list:
            if (isinstance(rec.get('Gender'),str) and rec.get('Gender') and rec.get('Gender').lower() not in ['male','female']) or (not isinstance(rec.get('Gender'),str)):
                rec['Gender'] = '-'

        file_path = '/home/progenesis/mnt/India/bioinfo/GUI_application/triploidy/new_pipeline/scripts/sample_list.txt'
        # Open the file in write mode, which clears its content
        with open(file_path, 'w') as file:
            # Truncate the file to remove existing content
            file.truncate()
        bulk_create = []
        accession_numbers = []
        for data_entry in data_list:
            string_to_append = f"{data_entry.get('EID')}\t{data_entry.get('#BarcodeID')}\t{data_entry.get('Gender','-')}\t{serializer.get('bam_directory_path')}"

            # Check if the file exists
            if os.path.exists(file_path):
                # If the file exists, open it in append mode and add the string on a new line
                with open(file_path, 'a') as file:
                    file.write(string_to_append + '\n')
            else:
                # If the file doesn't exist, create it and write the string to it
                with open(file_path, 'w') as file:
                    file.write(string_to_append + '\n')
            
            bulk_create.append(SampleHistory(run_id=serializer.get('bam_directory_path'),accession_number=data_entry.get('EID')))
            accession_numbers.append(str(data_entry.get('EID')))
        
        if bulk_create:
            SampleHistory.objects.bulk_create(bulk_create)

        # Construct the full command to change directory and run the Python file
        command = ['bash', '/home/progenesis/mnt/India/bioinfo/GUI_application/triploidy/new_pipeline/snakemake.sh']
        log_file_path = f'/app/media/output/{serializer.get("bam_directory_path")}.log'
        # # Use subprocess.Popen to run the command with pipes for stdout and stderr
        # process = subprocess.call(command)

        return_code = asyncio.run(run_command(command,log_file_path))

        if return_code == 0:
            SampleHistory.objects.filter(run_id=serializer.get('bam_directory_path'), accession_number__in=accession_numbers).update(is_complete=True)
            print("Command executed successfully.")
        else:
            SampleHistory.objects.filter(run_id=serializer.get('bam_directory_path'), accession_number__in=accession_numbers).update(is_complete=False)
            print(f"Command failed with exit code {return_code}.")
        move_matching_folders('/app/media','/app/media/processed',accession_numbers,serializer.get('bam_directory_path'))
    except Exception as e:
        StatusHandling.objects.create(run_id=serializer.get('bam_directory_path'),message=str(e),file_url=file_url)


@app.task
def process_upload_sample_parental(serializer,file_url, data_list):
    try:
        ParentalStatusHandling.objects.create(run_id=serializer.get('bam_directory_path'),message='Processing',file_url=file_url)

        file_path = '/home/progenesis/mnt/India/bioinfo/GUI_application/Parental_Identification/scripts/parental_identification.txt'
        # Open the file in write mode, which clears its content
        with open(file_path, 'w') as file:
            # Truncate the file to remove existing content
            file.truncate()
        bulk_create = []
        accession_numbers = []
        for data_entry in data_list:
            string_to_append = f"{data_entry.get('Accession Number')}\t{data_entry.get('Barcode')}\t{serializer.get('bam_directory_path')}"

            # Check if the file exists
            if os.path.exists(file_path):
                # If the file exists, open it in append mode and add the string on a new line
                with open(file_path, 'a') as file:
                    file.write(string_to_append + '\n')
            else:
                # If the file doesn't exist, create it and write the string to it
                with open(file_path, 'w') as file:
                    file.write(string_to_append + '\n')
            
            bulk_create.append(ParentalSampleHistory(run_id=serializer.get('bam_directory_path'),accession_number=data_entry.get('Accession Number')))
            accession_numbers.append(str(data_entry.get('Accession Number')))
        
        if bulk_create:
            ParentalSampleHistory.objects.bulk_create(bulk_create)

        # Construct the full command to change directory and run the Python file
        command = ['bash', '/home/progenesis/mnt/India/bioinfo/GUI_application/Parental_Identification/paternity_matching.sh']
        log_file_path = f'/app/media/parental_identification/output/{serializer.get("bam_directory_path")}.log'
        # # Use subprocess.Popen to run the command with pipes for stdout and stderr
        # process = subprocess.call(command)

        return_code = asyncio.run(run_command(command,log_file_path))

        if return_code == 0:
            ParentalSampleHistory.objects.filter(run_id=serializer.get('bam_directory_path'), accession_number__in=accession_numbers).update(is_complete=True)
            print("Command executed successfully.")
        else:
            ParentalSampleHistory.objects.filter(run_id=serializer.get('bam_directory_path'), accession_number__in=accession_numbers).update(is_complete=False)
            print(f"Command failed with exit code {return_code}.")
        move_matching_folders('/app/media/parental_identification','/app/media/parental_identification/processed',accession_numbers,serializer.get('bam_directory_path'))
    except Exception as e:
        ParentalStatusHandling.objects.create(run_id=serializer.get('bam_directory_path'),message=str(e),file_url=file_url)


@app.task
def process_upload_sample_parental_ploidy(serializer,file_url, data_list):
    try:
        ParentalPloidyStatusHandling.objects.create(run_id=serializer.get('bam_directory_path'),message='Processing',file_url=file_url)

        file_path = '/home/progenesis/mnt/India/bioinfo/GUI_application/parental_ploidy/scripts/sample_list.txt'
        # Open the file in write mode, which clears its content
        with open(file_path, 'w') as file:
            # Truncate the file to remove existing content
            file.truncate()
        bulk_create = []
        accession_numbers = []
        for data_entry in data_list:
            string_to_append = f"{data_entry.get('Accession Number')}\t{data_entry.get('Barcode')}\t{serializer.get('bam_directory_path')}"

            # Check if the file exists
            if os.path.exists(file_path):
                # If the file exists, open it in append mode and add the string on a new line
                with open(file_path, 'a') as file:
                    file.write(string_to_append + '\n')
            else:
                # If the file doesn't exist, create it and write the string to it
                with open(file_path, 'w') as file:
                    file.write(string_to_append + '\n')
            
            bulk_create.append(ParentalPloidySampleHistory(run_id=serializer.get('bam_directory_path'),accession_number=data_entry.get('Accession Number')))
            accession_numbers.append(str(data_entry.get('Accession Number')))
        
        if bulk_create:
            ParentalPloidySampleHistory.objects.bulk_create(bulk_create)

        # Construct the full command to change directory and run the Python file
        command = ['bash', '/home/progenesis/mnt/India/bioinfo/GUI_application/parental_ploidy/parental+triploid.sh']
        log_file_path = f'/app/media/parental_ploidy/output/{serializer.get("bam_directory_path")}.log'
        # # Use subprocess.Popen to run the command with pipes for stdout and stderr
        # process = subprocess.call(command)

        return_code = asyncio.run(run_command(command,log_file_path))

        if return_code == 0:
            ParentalPloidySampleHistory.objects.filter(run_id=serializer.get('bam_directory_path'), accession_number__in=accession_numbers).update(is_complete=True)
            print("Command executed successfully.")
        else:
            ParentalPloidySampleHistory.objects.filter(run_id=serializer.get('bam_directory_path'), accession_number__in=accession_numbers).update(is_complete=False)
            print(f"Command failed with exit code {return_code}.")
        move_matching_folders('/app/media/parental_ploidy','/app/media/parental_ploidy/processed',accession_numbers, serializer.get('bam_directory_path'))
    except Exception as e:
        ParentalPloidyStatusHandling.objects.create(run_id=serializer.get('bam_directory_path'),message=str(e),file_url=file_url)



def generic_send_email(subject,body,to):
    if isinstance(to,str):
        to = [to]
    send_mail(
        subject,
        body,
        EMAIL_HOST_USER,
        to,
        fail_silently=False,
    )

def move_matching_folders(src_folder, dest_folder, folder_names_to_match, run_id):
    # Check if source folder exists
    if not os.path.exists(src_folder):
        print(f"Source folder '{src_folder}' does not exist.")
        return

    # Create destination folder if it doesn't exist
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)
    
    run_id_path = os.path.join(dest_folder, run_id)
    if not os.path.exists(run_id_path):
        os.makedirs(run_id_path)

    # Iterate through subfolders and files in the source folder
    for item in os.listdir(src_folder):
        item_path = os.path.join(src_folder, item)

        # Check if it's a directory
        if os.path.isdir(item_path):
            # Check if it matches any name in the specified list
            if item in folder_names_to_match:
                dest_path = os.path.join(run_id_path, item)
                # Move the folder to the run_id_path, replace if exists
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)  # Remove existing destination folder
                shutil.move(item_path, dest_path)
                print(f"Moved folder '{item}' to '{run_id_path}'.")
        
        # Check if it's a file and contains run_id in its name
        elif os.path.isfile(item_path) and run_id in item:
            dest_path = os.path.join(run_id_path, item)
            # Move the file to the run_id_path, replace if exists
            if os.path.exists(dest_path):
                os.remove(dest_path)  # Remove existing destination file
            shutil.move(item_path, dest_path)
            print(f"Moved file '{item}' to '{run_id_path}'.")

def list_files_in_directory(directory):
    with os.scandir(directory) as entries:
        file_names = [entry.name for entry in entries if entry.is_file()]
    return file_names

def get_add_path(path):
    added_path = path.split('/app/media/')
    if len(added_path) > 1:
        return added_path[-1].split('/')
    return []

def get_file_url(directory, sample_id, file_extension='csv'):
    try:
        path = [BASE_URL,'media'] + get_add_path(directory)
        file_names = list_files_in_directory(directory)
        temp_name = f"{sample_id}.{file_extension}"
        if temp_name in file_names:
            return os.path.join(*path, temp_name)
        for name in file_names:
            if sample_id in name and file_extension == name.split('.')[-1]:
                return os.path.join(*path, name)
        return ''
    except Exception as e:
        return ''