global:
  resolve_timeout: 5m

route:
  receiver: ${ALERTMANAGER_DEFAULT_RECEIVER}
  group_by: [alertname, severity]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

  routes:
    - match:
        severity: critical
      receiver: ${ALERTMANAGER_DEFAULT_RECEIVER}
      repeat_interval: 1h

receivers:
  # No-op receiver used when SLACK_WEBHOOK_URL is not configured, so
  # Alertmanager has a valid default route without a real notification target.
  - name: "null"
  # SLACK_RECEIVER_START
  - name: slack-staging
    slack_configs:
      - api_url: ${SLACK_WEBHOOK_URL}
        channel: "#pandit-staging-alerts"
        title: "{{ .GroupLabels.alertname }} [{{ .Status | toUpper }}]"
        text: "{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}\n{{ end }}"
  # SLACK_RECEIVER_END

inhibit_rules:
  - source_match:
      severity: critical
    target_match:
      severity: warning
    equal: [alertname]
