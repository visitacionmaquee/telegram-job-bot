import pytest
from pathlib import Path
from api.metrics import JOBS_SCRAPED_TOTAL, JOBS_MATCHED_TOTAL, MATCH_SCORE_HISTOGRAM

BASE_DIR = Path(__file__).resolve().parent.parent

def test_metrics_endpoint_status_and_format(client):
    """Verify /metrics returns 200 and standard Prometheus scrapable text format"""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    text = response.text
    assert "# HELP" in text
    assert "# TYPE" in text
    assert "jobradar_http_requests_total" in text

def test_telemetry_http_middleware_increment(client):
    """Verify that calling API routes increments HTTP telemetry counters"""
    # Trigger a request
    client.get("/health")
    
    # Check metrics output
    metrics_res = client.get("/metrics")
    assert metrics_res.status_code == 200
    assert 'endpoint="/health"' in metrics_res.text
    assert 'status_code="200"' in metrics_res.text

def test_custom_domain_metrics_recording():
    """Verify Prometheus counter increments and histogram observations"""
    JOBS_SCRAPED_TOTAL.labels(source="linkedin").inc(5)
    JOBS_MATCHED_TOTAL.labels(role="Junior Software Engineer", quality_tier="high").inc(2)
    MATCH_SCORE_HISTOGRAM.observe(92)

    # Scrape latest metrics text
    from api.metrics import generate_latest
    output = generate_latest().decode("utf-8")
    assert 'jobradar_jobs_scraped_total{source="linkedin"}' in output
    assert 'jobradar_jobs_matched_total{quality_tier="high",role="Junior Software Engineer"}' in output
    assert "jobradar_match_score_distribution" in output

def test_prometheus_and_grafana_configs():
    """Verify Prometheus and Grafana config files and dashboards exist"""
    prom_yml = BASE_DIR / "monitoring" / "prometheus" / "prometheus.yml"
    ds_yml = BASE_DIR / "monitoring" / "grafana" / "provisioning" / "datasources" / "prometheus.yml"
    dash_yml = BASE_DIR / "monitoring" / "grafana" / "provisioning" / "dashboards" / "dashboards.yml"
    dash_json = BASE_DIR / "monitoring" / "grafana" / "dashboards" / "jobradar_overview.json"

    assert prom_yml.exists(), "prometheus.yml must exist"
    assert ds_yml.exists(), "Grafana datasource config must exist"
    assert dash_yml.exists(), "Grafana dashboard provider config must exist"
    assert dash_json.exists(), "jobradar_overview.json dashboard must exist"

    # Verify dashboard contains expected metric queries
    content = dash_json.read_text(encoding="utf-8")
    assert "jobradar_jobs_scraped_total" in content
    assert "jobradar_jobs_matched_total" in content
    assert "jobradar_http_requests_total" in content
