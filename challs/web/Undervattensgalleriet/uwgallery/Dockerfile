FROM ruby:4.0.1-alpine3.22
RUN apk add ruby-full ruby-dev sudo shadow bash gcc make musl-dev sqlite sqlite-libs
RUN useradd -ms /bin/bash web
RUN chmod u+s /usr/bin/sqlite3 /bin/cat
RUN echo 'web db = (ALL:ALL) NOPASSWD: /bin/ls' | sudo EDITOR='tee -a' visudo
WORKDIR /srv
COPY . /srv
RUN mkdir -p /srv/db
RUN chown -R web:web /srv /srv/*
RUN chown root:root flag.txt && chmod 600 flag.txt
USER web
RUN bundle install
EXPOSE 4567
CMD ["bundle", "exec", "puma", "-p", "4567", "--pidfile", "/tmp/puma.pid"]

