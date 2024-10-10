# Use the official Python image as the base image
FROM python:slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install necessary system packages and Python build tools
RUN apt-get update \
    && apt-get install -y \
    samtools wget unzip openjdk-17-jdk libgomp1 bcftools build-essential gcc g++ clang git cmake \
    && pip install --no-cache-dir setuptools \
    && apt-get clean

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

# Copy the requirements.txt file to the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --no-build-isolation -r requirements.txt

# Copy the rest of the application files
COPY . .

# Create a media directory for file storage
RUN mkdir -p media

# Collect static files for Django
RUN python manage.py collectstatic --noinput

# Gunicorn configuration
# CMD ["gunicorn", "--bind", "0.0.0.0:8001", "your_project_name.wsgi:application"]