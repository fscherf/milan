clip:
	docker run -it \
		-v ./:/app \
		-v /tmp/.X11-unix:/tmp/.X11-unix \
		-w /app \
		--shm-size=2gb \
		-e DISPLAY=:0 \
		fscherf/milan:latest \
		milan run ./entrypoints.py::open_trending_movies \
			--headless \
			--width=1280 \
			--height=720 \
			--capture=./youtube.mp4
