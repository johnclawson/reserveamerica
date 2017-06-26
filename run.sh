#!/usr/bin/env bash

# set default value

IMAGENAME="automation"
IMAGEVERSION="0.0.1"
LOGFOLDER="logs"
SELENIUMLOG="selenium.log"
PROTRACTORVERSION=5.1.1

mkdir $LOGFOLDER
cd $LOGFOLDER
touch $SELENIUMLOG
cd ..


#if [[ ! -z "${IMAGENAME}" ]]; then
#  IMAGENAME="automation"
#fi
#
#if [[ ! -z "${IMAGEVERSION}" ]]; then
#  IMAGEVERSION="0.0.1"
#fi
#
#if [[ ! -z "${LOGFOLDER}" ]]; then
#  LOGFOLDER="logs"
#fi
#
#if [[ ! -z "${SELENIUMLOG}" ]]; then
#  echo "SELENIUMLOG"
#  SELENIUMLOG="selenium.log"
#fi
#
#if [ ! -d "${LOGFOLDER}" ]; then
#  mkdir "${LOGFOLDER}"
#fi
#
#cd "${LOGFOLDER}"
#
#if [ ! -e "${SELENIUMLOG}" ]; then
#    touch "${SELENIUMLOG}"
#fi
#
#cd ..
#
#if [[ ! -z "${PROTRACTORVERSION}" ]]; then
#  PROTRACTORVERSION=5.1.1
#fi

delete_exist_image() {
    echo "# Delete image ${IMAGENAME}: ${IMAGEVERSION}"
    docker rmi -f ${IMAGENAME}:${IMAGEVERSION}
}

build_docker_image() {
    echo ""
    echo "# Build docker image now: ${IMAGENAME}:${IMAGEVERSION}"

    docker build -t ${IMAGENAME}:${IMAGEVERSION} \
        --build-arg protractorVersion=${PROTRACTORVERSION} \
        `printenv | grep -i proxy | awk '{print "--build-arg " $0}'` \
        -f docker/Dockerfile .
}


run_docker_image() {
    echo ""
    echo "# Run automation in docker now: ${IMAGENAME}:${IMAGEVERSION}"
    if [[ -z $(uname -a | grep Darwin) ]]; then
        xarg_cmd="xargs --no-run-if-empty"
    else
        xarg_cmd="xargs"
    fi

    docker ps -a -q --filter ancestor=${IMAGENAME}:${IMAGEVERSION} --format="{{.ID}}" | $xarg_cmd docker rm -f

    DOCKER_OPTS="--privileged --rm -v /dev/shm:/dev/shm -v $(pwd):/automation"
    DOCKER_OPTS="${DOCKER_OPTS} --env LOGFILE=/automation/${LOGFOLDER}/${SELENIUMLOG}"
    DOCKER_OPTS="${DOCKER_OPTS} -p 25900:5900 -p 24444:4444"

    docker run -it ${DOCKER_OPTS} ${IMAGENAME}:${IMAGEVERSION} \
        /automation/scripts/protractor.sh \
            -f /automation/cases/protractor/conf.js \
            -v

#   docker run -it ${DOCKER_OPTS} ${IMAGENAME}:${IMAGEVERSION} bash
}

start() {
    echo $IMAGE_NAME
    echo $IMAGE_VERSION
    if [[ "$(docker images -q ${IMAGENAME}:${IMAGEVERSION} 2> /dev/null)" == "" ]]; then
        is_previous_docker=0
    else
        is_previous_docker=1
    fi

    if [[ ${is_previous_docker} -gt 0 ]]; then
        echo "- Found exist docker image, delete first? ${clearExist}"
        if [[ "${clearExist}" = "true" ]]; then
            delete_exist_image
            build_docker_image
        fi
    else
        echo "- No exist docker image found"
        build_docker_image
    fi

    if [[ $? != 0 ]]; then
        exit $?
    fi
    if [[ "${onlyBuild}" == "false" ]]; then
        run_docker_image
    fi
}

main() {
    while getopts ":fb" optName "$@"; do
        case ${optName} in
        f)
            clearExist=true
            ;;
        b)
            onlyBuild=true
            ;;
        \?)
            usage
            ;;
        esac
    done

    shift $(($OPTIND - 1))
    # start
    run_docker_image
}

usage() {
cat <<EOF
Use protractor to do automation

Usage: ./run.sh [-f] [-b]

Arguments:

  -f
    Force to delete the exist image, before build new one and run the test cases

  -b
    Only build the docker image, don't run automation

Examples:

  Delete the exist protractor docker image, then just build a new one:
    ./run.sh -fb
EOF

exit 0
}

main "$@"
