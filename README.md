# Raspberry server for M5 data acquisition

1) Clone this repository running:
> inserire il comando git clone
2) Use Dockerfile to build image:
> cd \<**path to Dockerfile**>
> docker build -t RaspM5-server .
3) Run docker image to use the app:
> docker run -p 5000:5000 -p 3125:3125 RaspM5-server
