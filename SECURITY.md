# Security Notes

This repository is an MVP and is not intended to be exposed as an unauthenticated public multi-user service.

Before production deployment, add at minimum:

- authentication and per-user authorization;
- upload malware scanning and parser sandboxing;
- file-type/content validation beyond filename suffixes;
- encrypted temporary/object storage;
- automatic retention and deletion policies;
- a durable worker queue with resource/time limits;
- rate limits and quotas;
- secret management rather than plaintext environment files;
- restrictive CORS and reverse-proxy/TLS configuration;
- audit logs that do not contain document contents or API secrets.

Scientific manuscripts may be confidential or unpublished. The configured translation provider receives the natural-language content sent for translation; review that provider's data handling terms before processing sensitive documents.
