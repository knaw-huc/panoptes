FROM redocly/redoc
ARG VERSION_NUMBER=unreleased

RUN apk update && apk add gettext

ENV SPEC_URL=openapi.yaml
ENV PAGE_TITLE='Panoptes API Documentation'
ENV VERSION_NUMBER=$VERSION_NUMBER

COPY openapi.yaml /usr/share/nginx/html/openapi-raw.yaml
RUN /usr/bin/envsubst '$VERSION_NUMBER' < /usr/share/nginx/html/openapi-raw.yaml > /usr/share/nginx/html/openapi.yaml
RUN rm /usr/share/nginx/html/openapi-raw.yaml
