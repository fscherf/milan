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

    def _replace_file_extension(self, path, extension):
        base_name, _ = os.path.splitext(path)

        return f'{base_name}.{extension}'

    # ffmpeg: recording #######################################################
    def _get_ffmpeg_global_args(self):
        return [
            '-y',   # override existing files if needed
            '-an',  # disable audio
        ]

    def _get_ffmpeg_input_arguments(self):
        return [
            # We feed images without timestamps into ffmpeg. This tells ffmpeg
            # to use the wall clock instead to stabilize the framerate.
            '-use_wallclock_as_timestamps', '1',

            # read images from the stdin
            '-f', 'image2pipe',
            '-i', '-',
        ]

    def _get_ffmpeg_mp4_output_args(self, fps):
        return [
            '-f', 'mp4',              # format
            '-c:v', 'libx264',        # codec
            '-vf', 'format=yuv420p',  # video filter
            '-r', str(fps),           # framerate
        ]

    def _get_ffmpeg_webm_output_args(self, fps):
        return [
            '-f', 'webm',             # format
            '-c:v', 'libvpx-vp9',     # codec
            '-vf', 'format=yuv420p',  # video filter
            '-r', str(fps),           # framerate
        ]

    # ffmpeg: post processing #################################################
    def _convert_video_to_gif(self, input_path, output_path):
        self.logger.debug('converting %s to %s', input_path, output_path)

        Process(
            command=[
                self._ffmpeg_path,
                *self._get_ffmpeg_global_args(),

                '-i', input_path,
                '-filter_complex', '[0:v] palettegen [p]; [0:v][p] paletteuse',

                # Most gif player don't display framerates over
                # 30 correctly. Between 15 and 24 is recommended.
                '-r', '24',

                output_path,
            ],
            logger=self._get_sub_logger('ffmpeg.video2gif'),
        ).wait()

        self.logger.debug('converting %s to %s done', input_path, output_path)

    # public API ##############################################################
    def write_frame(self, image_data):
        if not self.state == 'recording':
            return

        try:
            self._ffmpeg_process.stdin_write(image_data)

        except Exception:
            self.logger.exception('exception raised while writing to ffmpeg')

    def start(self, output_path, fps=60):
        # TODO: check if ffmpeg really started
        # TODO: add hook to handle ffmpeg closing unexpectedly
        # TODO: add scaling

        output_format = os.path.splitext(output_path)[1][1:]

        if output_format not in ('mp4', 'webm', 'gif'):
            raise ValueError(f'invalid output format: {output_format}')

        self._touch(path=output_path)

        if self.state != 'idle':
            raise ValueError('recorder is not idling')

        # update internal state
        self._state = 'recording'
        self._output_path = output_path
        self._output_format = output_format

        # start ffmpeg for recording
        if output_format == 'gif':
            # Creating gifs is a post processing step.
            # We capture to .mp4 first and convert after the recording was
            # stopped.

            self._output_path = self._replace_file_extension(
                path=self._output_path,
                extension='mp4',
            )

            self._touch(path=self._output_path)

        # mp4
        if self._output_format in ('mp4', 'gif'):
            output_args = self._get_ffmpeg_mp4_output_args(fps=fps)

        # webm
        else:
            output_args = self._get_ffmpeg_webm_output_args(fps=fps)

        self.logger.debug('starting recording to %s', self._output_path)

        self._ffmpeg_process = Process(
            command=[
                self._ffmpeg_path,
                *self._get_ffmpeg_global_args(),
                *self._get_ffmpeg_input_arguments(),
                *output_args,
                self._output_path,
            ],
            logger=self._get_sub_logger('ffmpeg.recording'),
        )

    def stop(self):
        # TODO: remove mp4 video after gif rendering

        self.logger.debug('stopping recording to %s', self._output_path)

        if self.state != 'recording':
            self.logger.debug('nothing to do')

            return

        # stop ffmpeg
        self._state = 'stopping'

        self._ffmpeg_process.stdin_close()
        self._ffmpeg_process.wait()

        self._state = 'idle'

        # post processing
        # gif
        if self._output_format == 'gif':

            # convert previously generated mp4 video to gif
            self._convert_video_to_gif(
                input_path=self._output_path,
                output_path=self._replace_file_extension(
                    path=self._output_path,
                    extension='gif',
                ),
            )
