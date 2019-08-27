# metrics-accumulator

[![Build Status](https://ci.centos.org/view/Devtools/job/devtools-metrics-accumulator-f8a-build-master/badge/icon)](https://ci.centos.org/view/Devtools/job/devtools-metrics-accumulator-f8a-build-master/)

Metrics accumulator service captures metrics from different analytics services to be able to
convert into a prometheus compliant time series data. These data helps DevOps and SRE team to be
able to monitor and alert the platform developers in case of loss of quality of services.

This service does two things
- Metrics Collection
- Metrics Exposition

#### Metrics Collection
Based on the contents of a given payload, it tries to capture the response time latency metrics.

##### API Endpoint
POST `/api/v1/prometheus`

##### Payload Information
```
{
	"hostname": "localhost",
	"endpoint": "api_v1.test__slashless",
	"request_method": "GET",
	"status_code": 200,
	"pid" : 1234,
	"value": 0.04544
}
```

##### Response
```
200 - in case of success
{
    "message": "success"
}

400 - in case of invalid payload
{
    "message": "Make sure payload is valid and contains all the mandatory fields."
}

500 - in case of any other server errors

```

#### Metrics Exposition
This endpoint exposes prometheus compliant data.

##### API Endpoint
GET `/metrics`


#### How to run locally:

- `docker build --tag metrics:latest .`
- `docker run -it -p 5200:5200 metrics:latest`
- curl localhost:5200/api/v1/readiness should return `{}` with status 200


## Unit tests

There's a script named `runtests.sh` that can be used to run all unit tests. The unit test coverage is reported as well by this script.

Usage:

```
./runtests.sh

```

### Footnotes

#### Coding standards

- You can use scripts `run-linter.sh` and `check-docstyle.sh` to check if the code follows [PEP 8](https://www.python.org/dev/peps/pep-0008/) and [PEP 257](https://www.python.org/dev/peps/pep-0257/) coding standards. These scripts can be run w/o any arguments:

```
./run-linter.sh
./check-docstyle.sh
```

* The first script checks the indentation, line lengths, variable names, whitespace around operators etc. 
* The second script checks all documentation strings - its presence and format. Please fix any warnings and errors reported by these
scripts.

#### Code complexity measurement

The scripts `measure-cyclomatic-complexity.sh` and `measure-maintainability-index.sh` are used to measure code complexity. These scripts can be run w/o any arguments:

```
./measure-cyclomatic-complexity.sh
./measure-maintainability-index.sh
```

The first script measures cyclomatic complexity of all Python sources found in the repository. Please see [this table](https://radon.readthedocs.io/en/latest/commandline.html#the-cc-command) for further explanation how to comprehend the results.

The second script measures maintainability index of all Python sources found in the repository. Please see [the following link](https://radon.readthedocs.io/en/latest/commandline.html#the-mi-command) with explanation of this measurement.

You can specify command line option `--fail-on-error` if you need to check and use the exit code in your workflow. In this case the script returns 0 when no failures has been found and non zero value instead.

#### Dead code detection

The script `detect-dead-code.sh` can be used to detect dead code in the repository. This script can be run w/o any arguments:

```
./detect-dead-code.sh
```

Please note that due to Python's dynamic nature, static code analyzers are likely to miss some dead code. Also, code that is only called implicitly may be reported as unused.

Because of this potential problems, only code detected with more than 90% of confidence is reported.

#### Common issues detection

The script `detect-common-errors.sh` can be used to detect common errors in the repository. This script can be run w/o any arguments:

```
./detect-common-errors.sh
```

Please note that only semantical problems are reported.

#### Check for scripts written in BASH

The script named `check-bashscripts.sh` can be used to check all BASH scripts (in fact: all files with the `.sh` extension) for various possible issues, incompatibilities, and caveats. This script can be run w/o any arguments:

```
./check-bashscripts.sh
```

Please see [the following link](https://github.com/koalaman/shellcheck) for further explanation, how the ShellCheck works and which issues can be detected.

#### Code coverage report

Code coverage is reported via the codecov.io. The results can be seen on the following address:

[code coverage report](https://codecov.io/gh/fabric8-analytics/f8a-server-backbone)
