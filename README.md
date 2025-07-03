[![Docs (readthedocs)](https://readthedocs.org/projects/$NAME/badge/?version=latest&style=flat)](https://$NAME.readthedocs.io)
[![CI Test (github)](https://github.com/$USER/$REPO/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/$USER/$REPO/actions/)
[![Latest release (github)](https://img.shields.io/github/release/$USER/$REPO.svg)](https://github.com/$USER/$REPO/releases/)
[![Latest release (pypi)](https://img.shields.io/pypi/v/$NAME.svg)](https://pypi.org/project/$NAME/)
[![Project Status: Active – The project has reached a stable, usable state and is being actively developed.](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)

# Panoptes

Panoptes is a multi-tenant dataset browser and search tool. This repository contains the back-end code.

## Table of Contents

* [Introduction](#introduction)
* [Quick start](#quick start)
    * [Installation](#installation)
    * [Usage](#usage)
* [Documentation](#documentation)
* [Support & Roadmap](#support-and-roadmap)
* [Changelog](#changelog)
* [Contributing](#contributing)
* [Frequently Asked Questions](#frequently-asked-questions)

## Introduction

The Panoptes back-end is an API for searching through Elasticsearch indices and retrieving detailed information about specific
records using configurable data sources (so far the only supported option is the Clariah CMDI editor API, but more will be added in the future).

The API is made using FastAPI, dataset configuration is done in a Mongo database.

## Quick start

### Installation

This software is not released yet. Container images will be available here on GitHub. In order to use the latest version, you can build the container
image yourself. There is a Docker Bake configuration file. In order to set the name of the image, crate your own `docker-bake.override.hcl` file to set two variables:

```hcl
IMAGE = "some-registry.com/your-image-name"
TAG = "beta-1"
```
And then build & push using:
```shell
docker buildx bake --push
```

### Usage

As this is a multi-tenant service, you should configure the domain names belonging to the tenants in the database configuration. Then, it's possible to add
multiple datasets per tenant, pointing it to the correct 

TODO: Document database configuration. It is still in very early stages, documentation will follow when the configuration is definitive.

## Documentation

The API is specified in the [OpenAPI specification](docs/openapi.yaml). A compiled version using Redoc will be hosted as well.

## Support & Roadmap



## Changelog

Changes should be logged in the changelog using the [keep a changelog](https://keepachangelog.com/en/1.1.0/) specification. The changelog can be found [here](CHANGELOG.md).

## Contributing


## Frequently Asked Questions

None yet!
