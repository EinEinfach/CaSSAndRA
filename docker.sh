#!/bin/bash


HTTP_PORT=8050
export HOST_UID=$(id -u $USER)
export HOST_GID=$(id -g $USER)

echo "HTTP port: $HTTP_PORT"
echo "USER: $USER"
echo "UID: $HOST_UID"
echo "GID: $HOST_GID"


function build_docker {
    echo "build_docker"
    docker image rm --force cassandra
    #docker build -f docker.txt -t cassandra:slim .
    docker build . -t cassandra
}

function start_docker {
    echo "start_docker"
    #docker "run --user alex -e TZ=Europe/Berlin -p 2222:22 -p "$HTTP_PORT:$HTTP_PORT" \
    #    -v "/home/$USER/CaSSAndRA/CaSSAndRA/src:/usr/src/cassandra/src" --name cassandra cassandra:slim    
    docker run -it -p 8050:8050 -v "/home/$USER/.cassandra:/home/cassandra/.cassandra" -e HOST_UID="$HOST_UID" -e HOST_GID="$HOST_GID" cassandra 
}

function start_docker_terminal {
    echo "start_docker_terminal"
    docker run --entrypoint /bin/bash -it -p "$HTTP_PORT:$HTTP_PORT" -v "/home/$USER/.cassandra:/home/cassandra/.cassandra" -e HOST_UID="$HOST_UID" -e HOST_GID="$HOST_GID" cassandra  
}

function stop_docker {
    echo "stop_docker"
    ID=$(docker ps -a -q --filter="name=cassandra")
    echo $ID
    docker container stop $ID
    docker system prune
}

function list_docker {
    echo "list_docker"
    docker image ls
}

function remove_docker {
    echo "remove_docker"
    docker rmi --force $(docker images -f "dangling=true" -q)
    docker image rm --force cassandra
}

# show menu
PS3='Please enter your choice: '
options=("Build docker"
    "Start docker"
    "Start docker terminal"    
    "Stop docker"    
    "List docker images"
    "Remove docker image"        
    "Quit")
select opt in "${options[@]}"
do
    case $opt in
        "Build docker")
            build_docker
            break
            ;;
        "Start docker")
            start_docker
            break
            ;;            
        "Start docker terminal")
            start_docker_terminal
            break
            ;;            
        "Stop docker")
            stop_docker
            break
            ;;
        "List docker images")
            list_docker
            break
            ;;
        "Remove docker image")
            remove_docker
            break
            ;;
        "Quit")
            break
            ;;
        *) echo "invalid option $REPLY";;
    esac
done

