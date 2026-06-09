global:
  resolve_timeout: 5m

route:
  receiver: slack-staging
  group_by: [alertname, severity]
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

  routes:
    - match:
        severity: critical
      receiver: slack-staging
      repeat_interval: 1h

receivers:
  - name: slack-staging
    slack_configs:
      - api_url: ${SLACK_WEBHOOK_URL}
        channel: "#pandit-staging-alerts"
        title: "{{ .GroupLabels.alertname }} [{{ .Status | toUpper }}]"
        text: "{{ range .Alerts }}{{ .Annotations.summary }}\n{{ .Annotations.description }}\n{{ end }}"

inhibit_rules:
  - source_match:
      severity: critical
    target_match:
      severity: warning
    equal: [alertname]
