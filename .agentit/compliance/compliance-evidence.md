# Compliance Evidence Report

**Repository:** pinky
**Assessed:** 2026-07-11T08:35:28.001482+00:00
**Overall Score:** 80.6

## Security Controls

### container

- **Status:** partial
- **Severity:** medium
- **Evidence:** No Dockerfile or Containerfile found
- **Recommendation:** Create a multi-stage Containerfile using UBI base image

### container

- **Status:** fail
- **Severity:** high
- **Evidence:** No Containerfile or Dockerfile found
- **Recommendation:** Create multi-stage Containerfile with UBI base image

## Access Controls

### No findings

- **Status:** pass
- **Evidence:** No issues detected in this area.

## Audit Logging

### audit

- **Status:** fail
- **Severity:** high
- **Evidence:** No audit logging implementation detected
- **Recommendation:** Add audit logging for privileged actions and data access

## Data Protection

### No findings

- **Status:** pass
- **Evidence:** No issues detected in this area.
