FROM node:6.10-slim
LABEL maintainer shaokexu@gmail.com

# node + jdk8 + protractor
ARG protractorVersion
ENV NODE_PATH=/usr/local/lib/node_modules
RUN npm install -g protractor@${protractorVersion} \
    jasmine \
    jasmine-reporters@^2.2.0 \
    protractor-jasmine2-screenshot-reporter \
    chalk \
    --registry=https://registry.npmjs.org/

RUN echo oracle-java8-installer shared/accepted-oracle-license-v1-1 select true | /usr/bin/debconf-set-selections \
    && echo "deb http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main" | tee /etc/apt/sources.list.d/webupd8team-java.list \
    && echo "deb-src http://ppa.launchpad.net/webupd8team/java/ubuntu trusty main" | tee -a /etc/apt/sources.list.d/webupd8team-java.list \
    && apt-key adv --keyserver-options http-proxy=${http_proxy} --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys EEA14886 \
    && apt-get update \
    && apt-get install -y \
       wget \
       oracle-java8-installer \
    && rm -rf /var/cache/oracle-java8-installer
ENV JAVA_HOME /usr/lib/jvm/java-8-oracle

RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && sh -c 'echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list' \
    && apt-get update \
    && apt-get install -y \
       google-chrome-stable \
       netcat-openbsd \
       xvfb \
       x11vnc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir ~/.vnc \
    && x11vnc -storepasswd 123456789 ~/.vnc/passwd

# Fix for the issue with Selenium, as described here:
# https://github.com/SeleniumHQ/docker-selenium/issues/87
ENV DBUS_SESSION_BUS_ADDRESS=/dev/null \
    SCREEN_RES=1280x1024x24
EXPOSE 5900


