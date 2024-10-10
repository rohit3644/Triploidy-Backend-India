# Use the official Python image as the base image
FROM python:slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    samtools wget unzip openjdk-17-jdk libgomp1 bcftools \
    build-essential gcc g++ clang git cmake libpq-dev \
    python3-dev zlib1g-dev libbz2-dev liblzma-dev libncurses5-dev \
    libcurl4-openssl-dev libarrow-dev libparquet-dev \
    && rm -rf /var/lib/apt/lists/*

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
    && make install \
    && cd /app \
    && rm -rf bam-readcount

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the project files to the working directory
COPY . .

# Create the media directory
RUN mkdir -p media

# Collect static files
RUN python manage.py collectstatic --noinput
