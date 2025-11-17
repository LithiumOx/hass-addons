ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.19
# Use official Soft Serve image as a stage to copy the binary
FROM ghcr.io/charmbracelet/soft-serve:latest AS softserve

# Back to HA base; copy the static binary in
FROM ${BUILD_FROM}
COPY --from=softserve /usr/local/bin/soft /usr/local/bin/soft

# Minimal runtime deps (git for hooks and repo ops), jq for option parsing,
# and Python + PyYAML for rendering the Soft Serve config
RUN apk add --no-cache git bash jq python3 py3-yaml

# Add entrypoint
COPY run.sh /run.sh
RUN chmod +x /run.sh

EXPOSE 23231 23232
CMD ["/run.sh"]
