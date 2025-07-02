group "default" {
  targets = ["backend"]
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
