define DOCKER_RUN
	docker run -it \
		-v ./:/app \
		-v /tmp/.X11-unix:/tmp/.X11-unix \
		-w /app \
		--shm-size=2gb \
		-e DISPLAY=:0 \
		fscherf/milan:latest \
		$1
endef

clips:
	$(call DOCKER_RUN, tox)

browser:
	$(call DOCKER_RUN, milan run shell)
