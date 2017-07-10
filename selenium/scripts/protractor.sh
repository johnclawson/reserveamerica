#!/usr/bin/env bash

startSelenium() {
    port=4444
    echo "- Start to Run WebDriver/Selenium Start, log file: ${LOGFILE}"

    webdriver-manager update
    webdriver-manager start > $LOGFILE 2>&1 &

    sleep 3
    echo "- Selenium Started."
}

startX() {
    Xvfb :0  -screen 0 $SCREEN_RES &
    export DISPLAY=:0

    MAX=60 # About 60 seconds
    CT=0
    while ! xdpyinfo >/dev/null 2>&1; do
        sleep 0.50s
        CT=$(( CT + 1 ))
        if [ "$CT" -ge "$MAX" ]; then
            echo "- FATAL: $0: Gave up waiting for X server $DISPLAY"
            exit 11
        fi
    done

    sleep 2
}

startVNC() {
    if [[ ! -z "${VNCON}" ]]; then
        x11vnc -forever -usepw -display :0 &
        echo "- VNC server started, password: Welcome1, display: :0"
    fi
}

startProtractor() {
    if [[ -z "${BASEURL}" ]]; then
        cmd="protractor"
    else
        cmd="protractor --baseUrl=${BASEURL}"
    fi

    echo "- Command: ${cmd} $CONF"

    if [[ ! -z "${CONF}" ]]; then
      xvfb-run -a ${cmd} $CONF
    fi
}

start() {
    startX
    startVNC
    startSelenium
    startProtractor
}

main() {
    HOSTIP=""
    while getopts ":f:u:v" optName "$@"; do
        case ${optName} in
        f)
            CONF="${OPTARG}"
            ;;
        u)
            BASEURL="${OPTARG}"
            ;;
        v)
            VNCON="true"
            ;;
        \?)
            usage
            ;;
        esac
    done

    shift $(($OPTIND - 1))
    start
}

usage() {
cat <<EOF
 Start protractor in docker image

 Usage: $0 [-f <string>] [-u <string>] [-v]

 Arguments:

   -f
     Location of protractor config file

   -u
     Run test cases to test particular given ossa site
     Note: When -u provided any specific url, will ignore -h

   -v
     Start vnc server
EOF

 exit 0
}

main "$@"

