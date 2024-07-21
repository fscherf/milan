clips:
	docker run -it \
		-v ./:/app \
		-v /tmp/.X11-unix:/tmp/.X11-unix \
		-w /app \
		--shm-size=2gb \
		-e DISPLAY=:0 \
		fscherf/milan:latest \
		./standalone-script.py
