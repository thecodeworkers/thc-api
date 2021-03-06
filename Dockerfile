FROM python:3.8-alpine
WORKDIR /usr/app
RUN apk add --no-cache gcc musl-dev linux-headers
COPY requirements.txt /usr/app
RUN pip install -r requirements.txt
COPY . /usr/app
CMD ["flask", "run"]
