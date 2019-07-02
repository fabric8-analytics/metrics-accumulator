#! /bin/bash

COVERAGE_THRESHOLD=90

export TERM=xterm
TERM=${TERM:-xterm}

# set up terminal colors
NORMAL=$(tput sgr0)
RED=$(tput bold && tput setaf 1)
GREEN=$(tput bold && tput setaf 2)
YELLOW=$(tput bold && tput setaf 3)


threshold=0.6

export MAJORITY_THRESHOLD=$threshold
export DATA_DIR=.

PYTHONPATH=$(pwd)/src
export PYTHONPATH

printf "%sCreate Virtualenv for Python deps ..." "${NORMAL}"

function prepare_venv() {
    VIRTUALENV=$(which virtualenv)
    if [ $? -eq 1 ]
    then
        # python34 which is in CentOS does not have virtualenv binary
        VIRTUALENV=$(which virtualenv-3)
    fi

    ${VIRTUALENV} -p python3 venv && source venv/bin/activate && python3 "$(which pip3)" install -r requirements.txt
    if [ $? -ne 0 ]
    then
        printf "%sPython virtual environment can't be initialized%s" "${RED}" "${NORMAL}"
        exit 1
    fi
    printf "%sPython virtual environment initialized%s\n" "${YELLOW}" "${NORMAL}"
}

[ "$NOVENV" == "1" ] || prepare_venv || exit 1

# now we are surely in the Python virtual environment

pip install pytest
pip install pytest-cov
pip install radon==3.0.1

export prometheus_multiproc_dir="tests/logs"

echo "*****************************************"
echo "*** Cyclomatic complexity measurement ***"
echo "*****************************************"
radon cc -s -a -i venv .

echo "*****************************************"
echo "*** Maintainability Index measurement ***"
echo "*****************************************"
radon mi -s -i venv .

echo "*****************************************"
echo "*** Unit tests ***"
echo "*****************************************"
PYTHONDONTWRITEBYTECODE=1 python3 "$(which pytest)" --cov=src/ --cov-report term-missing --cov-fail-under=$COVERAGE_THRESHOLD -vv tests/
printf "%stests passed%s\n\n" "${GREEN}" "${NORMAL}"

codecov --token=5418ea7a-02dc-46b1-8ef8-921945bccb41
