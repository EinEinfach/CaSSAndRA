	FROM python:3.10-slim
	
	# install sudo, so we can run app as cassandra user
	RUN apt-get update && apt-get install -y sudo
	
	# add entrypoint script for handling host user/group ids
	COPY ./docker_entrypoint.sh /docker_entrypoint.sh
	RUN chmod 755 /docker_entrypoint.sh
	
	# setup a non-root user to execute the app
	RUN useradd -m cassandra
	WORKDIR /home/cassandra/app

	# install app dependencies before copying app files
	# this allows us to rebuild the image very quickly
	# unless we are changing anything in requirements.txt
    COPY ./requirements.txt .
	RUN pip install --upgrade pip
	RUN pip install -r requirements.txt
	
	# copy app files to our work directory (~/app)
	COPY ./CaSSAndRA .

	# define the volume where our files will be stored
	VOLUME ["/home/cassandra/.cassandra"]

	# start docker run commands with the entrypoint script first
	# remaining commands are executed immediately after and
	# include any additional options passed on the command line
	# 
	# Note: if required, you can override the entrypoint by
	#       passing the entrypoint option to the run command 
	#       Example: --entrypoint /bin/bash
	ENTRYPOINT ["/docker_entrypoint.sh", "python", "app.py"]
