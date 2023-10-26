FPS = 60
WIDTH = 1298
HEIGHT = 646
OUTPUT_FILE = 'video.webm'
FFMPEG_COMMAND = f'/usr/bin/ffmpeg -loglevel error -f image2pipe -avioflags direct -fpsprobesize 0 -probesize 32 -analyzeduration 0 -c:v mjpeg -i - -y -an -r {FPS} -c:v vp8 -qmin 0 -qmax 50 -crf 8 -deadline realtime -speed 8 -b:v 1M -threads 1 -vf pad={WIDTH}:{HEIGHT}:0:0:gray,crop={WIDTH}:{HEIGHT}:0:0 {OUTPUT_FILE}'  # NOQA
URL = "https://webgl-shaders.com/mountains-example.html"
