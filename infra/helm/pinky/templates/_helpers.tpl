{{- define "pinky.fullname" -}}
{{ .Release.Name }}
{{- end -}}

{{- define "pinky.labels" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "pinky.image" -}}
{{- $registry := .global.imageRegistry | default "" -}}
{{- if $registry -}}
{{ $registry }}/{{ .image.repository }}:{{ .image.tag }}
{{- else -}}
{{ .image.repository }}:{{ .image.tag }}
{{- end -}}
{{- end -}}

{{- define "pinky.dbSecretName" -}}
{{- if .Values.postgresql.auth.existingSecret -}}
{{ .Values.postgresql.auth.existingSecret }}
{{- else -}}
{{ include "pinky.fullname" . }}-db-credentials
{{- end -}}
{{- end -}}

{{- define "pinky.encryptionSecretName" -}}
{{- if .Values.encryption.existingSecret -}}
{{ .Values.encryption.existingSecret }}
{{- else -}}
{{ include "pinky.fullname" . }}-encryption-key
{{- end -}}
{{- end -}}

{{- define "pinky.temporalAddress" -}}
{{- if .Values.temporal.external.address -}}
{{ .Values.temporal.external.address }}
{{- else -}}
{{ include "pinky.fullname" . }}-temporal:7233
{{- end -}}
{{- end -}}

{{- define "pinky.redisUrl" -}}
{{- if .Values.redis.external.url -}}
{{ .Values.redis.external.url }}
{{- else -}}
redis://{{ include "pinky.fullname" . }}-redis:6379/0
{{- end -}}
{{- end -}}

{{- define "pinky.dbUrl" -}}
postgresql+asyncpg://{{ .Values.postgresql.auth.username }}:$(DB_PASSWORD)@{{ include "pinky.fullname" . }}-postgresql:5432/{{ .Values.postgresql.auth.database }}
{{- end -}}

{{- define "pinky.dbUrlPlain" -}}
postgresql://{{ .Values.postgresql.auth.username }}:$(DB_PASSWORD)@{{ include "pinky.fullname" . }}-postgresql:5432/{{ .Values.postgresql.auth.database }}
{{- end -}}
