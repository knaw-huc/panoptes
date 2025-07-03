group "default" {
  targets = ["backend", "docs"]
}

variable "IMAGE" {
  default = "panoptes-backend"
}

variable "TAG" {
  default = "latest"
}

target "backend" {
  context = "."
  dockerfile = "Dockerfile"
  tags = ["${IMAGE}:${TAG}", "${IMAGE}:latest"]
  platforms = ["linux/amd64"]
}

target "docs" {
  context = "docs"
  dockerfile = "Dockerfile"
  tags = ["${IMAGE}-docs:${TAG}", "${IMAGE}-docs:latest"]
  platforms = ["linux/amd64"]
}
