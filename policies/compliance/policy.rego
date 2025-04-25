package compliance

# Deny helm-upgrade tasks to non-staging namespaces
deny[msg] {
  input.task.type == "helm-upgrade"
  namespace := input.task.payload.namespace
  namespace != "staging"
  msg = sprintf("Helm upgrade must deploy to 'staging', not '%s'.", [namespace])
}

# Deny deployments without required image tag format (semantic version)
deny[msg] {
  input.task.type == "helm-upgrade"
  tag := input.task.payload.image_tag
  not re_match("^v?[0-9]+\\.[0-9]+\\.[0-9]+$", tag)
  msg = sprintf("Image tag '%s' is not a valid semver (e.g. '1.2.3').", [tag])
}

# Deny docker-build contexts outside designated directories
deny[msg] {
  input.task.type == "docker-build"
  context := input.task.payload.context
  not startswith(context, "./services/")
  msg = sprintf("Docker build context '%s' must be under './services/'.", [context])
}

# Deny missing release notes template for llm-doc tasks
deny[msg] {
  input.task.type == "llm-doc"
  not input.task.payload.template
  msg = "llm-doc task missing 'template' parameter."
}

# Warn on high concurrency for resource safety (example of non-deny)
warn[msg] {
  input.task.type == "docker-build"
  concurrency := input.run.concurrency
  concurrency > 5
  msg = sprintf("High build concurrency (%d) may overwhelm registry.", [concurrency])
}
