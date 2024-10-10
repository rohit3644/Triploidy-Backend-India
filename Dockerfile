# Use the official Python image as the base image
FROM python:slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    samtools wget unzip openjdk-17-jdk libgomp1 bcftools \
    build-essential gcc g++ clang git cmake libpq-dev \
    python3-dev zlib1g-dev libbz2-dev liblzma-dev libncurses5-dev \
    libcurl4-openssl-dev \
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
    && make install

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p media

# Collect static files
RUN python manage.py collectstatic --noinput
