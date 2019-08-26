"""Implementation of the REST API for the prometheus metrics service."""

import os
import flask
import logging
from flask import Flask, request
from prometheus_client import CollectorRegistry, generate_latest, multiprocess, CONTENT_TYPE_LATEST
from prometheus_client import Counter, Histogram, Gauge
from raven.contrib.flask import Sentry

registry = CollectorRegistry()
multiprocess.MultiProcessCollector(registry)

reset_counter = False
if os.environ.get('RESET_COUNTER_ON_RESTART', '0') == '1':
    reset_counter = True


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
        ('pid', 'method', duration_group_name, 'status'),
        registry=registry,
        **buckets
    )

    # Add group by endpoint or path for our Counter metrics
    request_count_gauge = Gauge(
        '%s_http_request_count' % prefix,
        'Total number of HTTP requests aggregated by method, endpoint, response_code',
        ('pid', 'method', duration_group_name, 'status'),
        registry=registry
    )
    # Add group by endpoint or path for our Counter metrics
    time_count_guage = Gauge(
        '%s_http_request_latency_time' % prefix,
        'Total time to serve HTTP requests aggregated by method, endpoint, response_code',
        ('pid', 'method', duration_group_name, 'status'),
        registry=registry
    )

    return gauge, histogram, request_count_gauge, time_count_guage


# Initialize flask app
app = Flask(__name__)

# Setup Logging
setup_logging(app)

# Get gauge, histogram and counter handles
gauge, histogram, request_count_gauge, time_count_guage = init_prometheus_client()
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
sentry = Sentry(app, dsn=SENTRY_DSN, logging=True, level=logging.ERROR)
app.logger.info('App initialized, ready to roll...')


def create_custom_gauge_metrics():
    """Create custom gauge metrics to maintain moving average.

    Group by Method Type, Endpoint Name, Status Code.
    """
    global total_gauge_time
    total_gauge_time = {}
    global total_gauge_count
    total_gauge_count = {}
    global reset_counter
    populate_guage_dicts()

    # Clear Guages
    if reset_counter:
        for key in total_gauge_time.keys() and total_gauge_count:
            group_by = key.split(' ')
            request_count_gauge.labels(group_by[0], group_by[1], group_by[2], group_by[3]).set(0)
            time_count_guage.labels(group_by[0], group_by[1], group_by[2], group_by[3]).set(0)
            gauge.labels(group_by[1], group_by[2], group_by[3]).set(0)
        app.logger.info("Gauges Reset")
        reset_counter = False
        populate_guage_dicts()

    for key in total_gauge_time.keys() and total_gauge_count:
        group_by = key.split(' ')
        if total_gauge_count[key]:
            gauge.labels(group_by[1], group_by[2], group_by[3]).set(
                total_gauge_time[key] / total_gauge_count[key]
            )


def populate_guage_dicts():
    """Will Populate total_gauge_time and total_gauge_count.

    :return: None
    """
    for metric in registry.collect():
        if 'multiprocess' in metric.documentation.lower():
            if metric.name == time_count_guage._name:
                for sample in metric.samples:
                    key = "{} {} {} {}".format(
                        sample[1]['pid'], sample[1]['method'],
                        sample[1]['endpoint'], sample[1]['status'])
                    if key in total_gauge_time:
                        total_gauge_time[key] += sample[2]
                    else:
                        total_gauge_time[key] = sample[2]

            if metric.name == request_count_gauge._name:
                for sample in metric.samples:
                    key = "{} {} {} {}".format(
                        sample[1]['pid'], sample[1]['method'],
                        sample[1]['endpoint'], sample[1]['status'])
                    if key in total_gauge_count:
                        total_gauge_count[key] += sample[2]
                    else:
                        total_gauge_count[key] = sample[2]


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
    payload = ['endpoint', 'value', 'request_method', 'status_code', 'pid']
    input_json = request.get_json()
    try:
        assert all(inputs in input_json for inputs in payload)
        assert type(input_json['value']) == float
        value = input_json['value']
        endpoint = input_json['endpoint']
        if endpoint == 'api_v1.get_component_analysis' and value > 2:
            # In Component analysis if value is more than 2secs, write log error
            app.logger.error(
             'Component Analysis exceeds threshold value | Input payload: {0}'.format(input_json))

        pid = str(input_json.get('pid'))
        # We should not use hostname as it dilutes the data at pretty fast clip
        # hostname = input_json.get('hostname')
        status_code = str(input_json['status_code'])
        request_method = input_json['request_method']

        # Remove any unwanted __slashless and __slashfull from the endpoint name
        group = input_json['endpoint'].split('__')[0]

        # Create a Histogram
        histogram.labels(pid, request_method, group, status_code).observe(value)

        # Create Counters for total time and hits
        request_count_gauge.labels(pid, request_method, group, status_code).inc()
        time_count_guage.labels(pid, request_method, group, status_code).inc(value)

        # Create custom gauge excluding pid for our grafana-graphite-osdmonitor combination
        create_custom_gauge_metrics()
        app.logger.info(input_json)
    except (AssertionError, TypeError) as e:
        status = 400
        message = 'Make sure payload is valid and contains all the mandatory fields.'
        app.logger.error('{0} | Input payload: {1}'.format(e, input_json))
    except Exception as e:
        status = 500
        app.logger.error('{0} | Input payload: {1}'.format(e, input_json))

    resp = {'message': message}
    return flask.jsonify(resp), status


if __name__ == "__main__":
    app.run()
