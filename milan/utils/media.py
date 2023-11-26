import subprocess
import json
import os

from milan.executables import find_ffprobe_executable


class Media:
    FFPROBE_ARGS = [
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        '-i',
    ]

    def __init__(self, input_path):
        self.input_path = input_path

        self.meta_data = {}

        # check if input exists
        if not os.path.exists(self.input_path):
            raise FileNotFoundError(self.input_path)

        # run ffprobe
        self.ffprobe_path = find_ffprobe_executable()

        self.ffprobe_command = [
            self.ffprobe_path,
            *self.FFPROBE_ARGS,
            self.input_path,
        ]

        json_output = subprocess.check_output(
            self.ffprobe_command,
            stderr=subprocess.DEVNULL,
        ).decode()

        self.meta_data.update(json.loads(json_output))

    def __repr__(self):
        return f'<{self.__class__.__name__}({self.input_path=})>'

    # format properties
    @property
    def size(self):
        return int(self.meta_data['format'].get('size', 0))

    # stream info properties
    @property
    def width(self):
        return int(self.meta_data['streams'][0].get('width', 0))

    @property
    def height(self):
        return int(self.meta_data['streams'][0].get('height', 0))


class Video(Media):

    # format properties
    @property
    def format(self):
        return self.meta_data['format'].get('format_name', '').split(',')

    @property
    def duration(self):
        return float(self.meta_data['format'].get('duration', 0.0))

    # stream info properties
    @property
    def fps(self):
        value = self.meta_data['streams'][0].get('r_frame_rate', '')

        if not value:
            return 0

        frames, seconds = value.split('/')

        return int(frames) / int(seconds)

    @property
    def codec(self):
        return self.meta_data['streams'][0].get('codec_name', '')


class Image(Media):

    # stream info properties
    @property
    def format(self):
        return self.meta_data['streams'][0].get('codec_name', '')
