group "default" {
  targets = ["backend"]
}

target "backend" {
  context = "."
  dockerfile = "Dockerfile"
  tags = ["panoptes-backend:latest"]
  platforms = ["linux/amd64"]
}
