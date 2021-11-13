#Python Debian Build
#FROM python:slim
#WORKDIR /nws
#COPY apiScan.py /nws
#RUN pip3 install facebook-sdk tweepy
#CMD ["python", "apiScan.py"]

#Python Alpine Build
FROM python:alpine
WORKDIR /nws
COPY apiScan.py /nws
RUN pip3 install facebook-sdk tweepy
CMD ["python", "apiScan.py"]

#tag :alpine, :debian, :VERNUM, :VERNUM-debian, :latest