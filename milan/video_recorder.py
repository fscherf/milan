import logging
import os

from milan.executables import find_ffmpeg_executable
from milan.utils.process import Process
from milan.utils.misc import unique_id


class VideoRecorder:
    def __init__(self, logger=None):
        self.logger = logger

        if not logger:
            self.logger = logging.getLogger(
                f'milan.video-recorder.{unique_id()}',
            )

        # internal state
        self._ffmpeg_path = find_ffmpeg_executable()
        self._ffmpeg_process = None
        self._output_path = ''
        self._output_format = ''
        self._output_gif_path = ''
        self._state = 'idle'

    def __repr__(self):
        return f'<VideoRecorder({self.ffmpeg_path=}, {self.state=})>'

    @property
    def ffmpeg_path(self):
        return self._ffmpeg_path

    @property
    def state(self):
        return self._state

    # helper ##################################################################
    def _get_sub_logger(self, name):
        return logging.getLogger(f'{self.logger.name}.{name}')

    def _touch(self, path):
        with open(path, 'w+') as file_handle:
            file_handle.close()

    # ffmpeg args #############################################################
    def _get_ffmpeg_global_args(self):
        return [
            '-y',   # override existing files if needed
            '-an',  # disable audio
        ]

    def _get_ffmpeg_input_args(self):
        return [
            # We feed images without timestamps into ffmpeg. This tells ffmpeg
            # to use the wall clock instead to stabilize the framerate.
            '-use_wallclock_as_timestamps', '1',

            # read images from the stdin
            '-f', 'image2pipe',
            '-i', '-',
        ]

    def _get_ffmpeg_mp4_output_args(self, fps, width, height):
        fps = fps or 60

        # h264 needs both dimensions to be divisible by two.
        # `-2` tells ffmpeg to generate the all missing dimensions, to keep the
        # aspect ratio, and then decrease it until it is divisible by two.
        width = int(width or -2)
        height = int(height or -2)

        # scaling
        if width or height:
            filter_string = f'format=yuv420p,scale={width}:{height}'

        # no scaling
        else:
            filter_string = 'format=yuv420p'

        return [
            '-f', 'mp4',           # format
            '-c:v', 'libx264',     # codec
            '-vf', filter_string,  # filter
            '-r', str(fps),        # framerate
        ]

    def _get_ffmpeg_webm_output_args(self, fps, width, height):
        fps = fps or 60
        width = int(width or -2)
        height = int(height or -2)

        # scaling
        if width or height:
            filter_string = f'format=yuv420p,scale={width}:{height}'

        # no scaling
        else:
            filter_string = 'format=yuv420p'

        return [
            '-f', 'webm',          # format
            '-c:v', 'libvpx-vp9',  # codec
            '-vf', filter_string,  # filter
            '-r', str(fps),        # framerate
        ]

    def _get_ffmpeg_gif_output_args(self, fps, width, height):
        fps = fps or 24
        width = int(width or -2)
        height = int(height or -2)

        if fps > 24:
            self.logger.warning(
                'Most gif player don\'t display framerates over'
                '30 correctly. Between 15 and 24 is recommended.'
            )

        # scaling
        if width or height:
            filter_complex_string = (
                f'[0:v] scale={width}:{height} [scaled];'
                '[scaled] split [scaled_0][scaled_1];'
                '[scaled_0] palettegen [palette];'
                '[scaled_1][palette] paletteuse'
            )

        # no scaling
        else:
            filter_complex_string = (
                '[0:v] palettegen [palette];'
                '[0:v] [palette] paletteuse'
            )

        return [
            '-f', 'gif',  # format
            '-filter_complex', filter_complex_string,
            '-r', str(fps),
        ]

    # public API ##############################################################
    def write_frame(self, image_data):
        if not self.state == 'recording':
            return

        try:
            self._ffmpeg_process.stdin_write(image_data)

        except Exception:
            self._state = 'crashed'

            self.logger.exception('exception raised while writing to ffmpeg')

    def start(self, output_path, width=0, height=0, fps=0):
        # TODO: check if ffmpeg really started
        # TODO: add hook to handle ffmpeg closing unexpectedly

        self.logger.debug('starting recording to %s', self._output_path)

        output_format = os.path.splitext(output_path)[1][1:]

        if output_format not in ('mp4', 'webm', 'gif'):
            raise ValueError(f'invalid output format: {output_format}')

        if width % 2 != 0 or height % 2 != 0:
            raise ValueError('both width and height have to be divisible by 2')

        # update internal state
        if self.state != 'idle':
            raise ValueError('recorder is not idling')

        self._state = 'recording'
        self._output_path = output_path
        self._output_format = output_format

        # setup ffmpeg command
        # mp4
        if self._output_format == 'mp4':
            output_args = self._get_ffmpeg_mp4_output_args(
                fps=fps,
                width=width,
                height=height,
            )

        # webm
        elif self._output_format == 'webm':
            output_args = self._get_ffmpeg_webm_output_args(
                fps=fps,
                width=width,
                height=height,
            )

        # gif
        elif self._output_format == 'gif':
            output_args = self._get_ffmpeg_gif_output_args(
                fps=fps,
                width=width,
                height=height,
            )

        # check if output path is writeable
        self._touch(path=output_path)

        # start ffmpeg
        self._ffmpeg_process = Process(
            command=[
                self._ffmpeg_path,
                *self._get_ffmpeg_global_args(),
                *self._get_ffmpeg_input_args(),
                *output_args,
                self._output_path,
            ],
            logger=self._get_sub_logger('ffmpeg.recording'),
        )

    def stop(self):
        self.logger.debug('stopping recording to %s', self._output_path)

        if self.state != 'recording':
            self.logger.debug('nothing to do')

            return

        self._state = 'stopping'

        if self._ffmpeg_process:
            self._ffmpeg_process.stdin_close()
            self._ffmpeg_process.wait()

        self._state = 'idle'
