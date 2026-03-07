# Base image
FROM python:3.9-alpine

# add required packages
RUN apk add --no-cache bluez

# Set the working directory
WORKDIR /app

# Copy project files
COPY . .

# Install requirements
RUN pip install -r requirements.txt

# Set the command to run the server
CMD ["python", "yeehack.py", "server"]
