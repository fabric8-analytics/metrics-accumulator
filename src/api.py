"""Implementation of the REST API for the prometheus metrics service."""

import os
import flask
import logging
from flask import Flask, request
from prometheus_client import CollectorRegistry, generate_latest, multiprocess, CONTENT_TYPE_LATEST
from prometheus_client import Counter, Histogram, Gauge

registry = CollectorRegistry()
print(os.environ.get('prometheus_multiproc_dir'))
multiprocess.MultiProcessCollector(registry)


def setup_logging(flask_app):
    """Perform the setup of logging (file, log level) for this application."""
    if not flask_app.debug:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'))
        log_level = os.environ.get('FLASK_LOGGING_LEVEL', logging.getLevelName(logging.WARNING))
        handler.setLevel(log_level)

        flask_app.logger.addHandler(handler)
        flask_app.config['LOGGER_HANDLER_POLICY'] = 'never'
        flask_app.logger.setLevel(logging.DEBUG)


def init_prometheus_client():
    """Initialize the multi-process prometheus client."""
    duration_group_name = 'endpoint'
    prefix = 'analytics_api'
    buckets = {'buckets': (1.0, 2.0, 3.0, 4.0, 5.0, 8.0, 13.0, 21.0, 34.0, float("inf"))}

    # Add gauge metrics for our average calculations
    # Gauge by default considers pid for labeling for multiprocess_mode in (all, liveall).
    gauge = Gauge(
        '%s_http_request_gauge' % prefix,
        'Average Response Time of HTTP requests aggregated by method, endpoint, response_code',
        ('method', duration_group_name, 'status'),
        registry=registry, multiprocess_mode='liveall'
    )

    # We need to extend pid labeling to our Histogram as well
    histogram = Histogram(
        '%s_http_request_duration_seconds' % prefix,
        'Flask HTTP request duration in seconds aggregated by pid, method, endpoint, response_code',
        ('method', duration_group_name, 'status'),
        registry=registry,
        **buckets
    )

    # Add group by endpoint or path for our Counter metrics
    counter = Counter(
        '%s_http_request_count' % prefix,
        'Total number of HTTP requests aggregated by method, endpoint, response_code',
        ('method', duration_group_name, 'status'),
        registry=registry
    )
    # Add group by endpoint or path for our Counter metrics
    counter_time = Counter(
        '%s_http_request_latency_time' % prefix,
        'Total time to serve HTTP requests aggregated by method, endpoint, response_code',
        ('method', duration_group_name, 'status'),
        registry=registry
    )

    return gauge, histogram, counter, counter_time


# Initialize flask app
app = Flask(__name__)

# Setup Logging
setup_logging(app)

# Get gauge, histogram and counter handles
gauge, histogram, counter, counter_time = init_prometheus_client()


@app.route('/metrics')
def metrics_exposition():
    """Endpoint to expose prometheus formatted metrics."""
    headers = {'Content-Type': CONTENT_TYPE_LATEST}
    return generate_latest(registry), 200, headers


@app.route('/api/v1/readiness')
def readiness():
    """Handle GET requests that are sent to /api/v1/readiness REST API endpoint."""
    return flask.jsonify({}), 200


@app.route('/api/v1/liveness')
def liveness():
    """Handle GET requests that are sent to /api/v1/liveness REST API endpoint."""
    return flask.jsonify({}), 200


@app.route('/api/v1/prometheus', methods=['POST'])
def metrics_colletion():
    """Persist the prometheus metrics from different analytics services."""
    status = 200
    message = 'success'
    payload = ['endpoint', 'value', 'request_method', 'status_code']
    try:
        input_json = request.get_json()
        assert all(inputs in input_json for inputs in payload)
        assert type(input_json['value']) == float
        value = input_json['value']
        pid = str(input_json.get('pid'))
        hostname = input_json.get('hostname')
        status_code = str(input_json['status_code'])
        request_method = input_json['request_method']

        # Remove any unwanted __slashless and __slashfull from the endpoint name
        group = input_json['endpoint'].split('__')[0]

        histogram.labels(request_method, group, status_code).observe(value)

        counter.labels(request_method, group, status_code).inc()
        counter_time.labels(request_method, group, status_code).inc(value)

        # Get moving average data per (endpoint, method_tye, status_code, pid)
        total_count = 1
        total_time = 0
        for sample in counter._samples():
            if '_total' in sample:
                total_count = sample[2]
        for sample in counter_time._samples():
            if '_total' in sample:
                total_time = sample[2]

        if total_time > 0 and total_count > 0:
            # Gauge by default aggregates based on PID if multiprocess_mode in (all, liveall)
            gauge.labels(request_method, group, status_code).set(float(total_time / total_count))

    except (AssertionError, TypeError) as e:
        status = 400
        message = 'Make sure payload is valid and contains all the mandatory fields.'
        app.logger.error('%r' % e)
    except Exception as e:
        status = 500
        message = '%r' % e
        app.logger.error(message)

    resp = {'message': message}
    return flask.jsonify(resp), status


if __name__ == "__main__":
    app.run()
