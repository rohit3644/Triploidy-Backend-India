# Use the official Python image as the base image
FROM python:slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

RUN apt-get update \
&& apt-get install samtools wget unzip openjdk-17-jdk libgomp1 bcftools build-essential gcc g++ clang git cmake -y

# Download and install GATK
RUN wget https://github.com/broadinstitute/gatk/releases/download/4.5.0.0/gatk-4.5.0.0.zip \
    && unzip gatk-4.5.0.0.zip \
    && mv gatk-4.5.0.0 /usr/local/ \
    && rm gatk-4.5.0.0.zip

# Add GATK to the PATH
ENV GATK_HOME /usr/local/gatk-4.5.0.0
ENV PATH $PATH:$GATK_HOME

# Clone bam-readcount, build, and install
RUN git clone https://github.com/genome/bam-readcount \
    && cd bam-readcount \
    && mkdir build \
    && cd build \
    && cmake .. \
    && make \
    && make install


RUN apt-get update \
    && apt-get install -y \
    libpq-dev zlib1g-dev libbz2-dev liblzma-dev \
    libboost-dev libboost-system-dev libboost-filesystem-dev libarrow-dev libparquet-dev \
    && apt-get clean

COPY requirements.txt .

# Install any dependencies
RUN pip install -r requirements.txt

# Copy the dependencies file to the working directory
COPY . .

RUN mkdir -p media

# Collect static files
RUN python manage.py collectstatic --noinput

# Gunicorn configuration
# CMD ["gunicorn", "--bind", "0.0.0.0:8001", "your_project_name.wsgi:application"]

# CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]