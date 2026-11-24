import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def test_production_docker_compose_structure():
    """Verify production docker-compose file includes all services and volumes"""
    prod_compose = BASE_DIR / "docker-compose.prod.yml"
    assert prod_compose.exists(), "docker-compose.prod.yml must exist"

    content = prod_compose.read_text(encoding="utf-8")
    expected_services = ["db:", "redis:", "api:", "worker:", "bot:", "nginx:", "certbot:"]
    for s in expected_services:
        assert s in content, f"Service {s} missing from production compose"

    assert "jobradar_internal:" in content
    assert "certbot_conf:" in content
    assert "certbot_www:" in content

def test_nginx_configuration_files():
    """Verify Nginx reverse proxy configuration and security headers"""
    nginx_conf = BASE_DIR / "nginx" / "nginx.conf"
    default_conf = BASE_DIR / "nginx" / "conf.d" / "default.conf"

    assert nginx_conf.exists(), "nginx.conf must exist"
    assert default_conf.exists(), "default.conf must exist"

    n_content = nginx_conf.read_text(encoding="utf-8")
    d_content = default_conf.read_text(encoding="utf-8")

    # Core Nginx directives
    assert "worker_processes" in n_content
    assert "limit_req_zone" in n_content
    assert "gzip on;" in n_content

    # Proxy and security directives
    assert "upstream jobradar_api" in d_content
    assert "proxy_pass http://jobradar_api" in d_content
    assert "Strict-Transport-Security" in d_content
    assert "X-Frame-Options" in d_content
    assert "ssl_protocols TLSv1.2 TLSv1.3;" in d_content
    assert "location /.well-known/acme-challenge/" in d_content

def test_oci_deployment_scripts():
    """Verify OCI VM bootstrap and SSL scripts are properly structured"""
    setup_script = BASE_DIR / "deploy" / "setup_oci_vm.sh"
    ssl_script = BASE_DIR / "deploy" / "init_ssl.sh"
    guide = BASE_DIR / "deploy" / "OCI_DEPLOYMENT_GUIDE.md"

    assert setup_script.exists(), "setup_oci_vm.sh must exist"
    assert ssl_script.exists(), "init_ssl.sh must exist"
    assert guide.exists(), "OCI_DEPLOYMENT_GUIDE.md must exist"

    setup_content = setup_script.read_text(encoding="utf-8")
    assert "docker-compose-plugin" in setup_content
    assert "iptables" in setup_content
    assert "jobradar.service" in setup_content

    ssl_content = ssl_script.read_text(encoding="utf-8")
    assert "certbot certonly" in ssl_content
    assert "nginx -s reload" in ssl_content
