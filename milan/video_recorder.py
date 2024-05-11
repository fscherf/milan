import tempfile
import logging
import os

from milan.utils.misc import unique_id, AtomicCounter
from milan.executables import get_executable
from milan.utils.process import Process


class VideoRecorder:
    def __init__(self, logger=None):
        self.logger = logger

        if not logger:
            self.logger = logging.getLogger(
                f'milan.video-recorder.{unique_id()}',
            )

        self._state = 'idle'
        self._frame_counter = AtomicCounter()

    def __repr__(self):
        return f'<VideoRecorder({self.state=})>'

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
            '-f', 'image2',  # format

            # This tells ffmpeg to use the file modification timestamps as
            # frame timestamps. `2` sets the precision to nanosecond.
            '-ts_from_file', '2',

            '-i', f'{self._frame_dir_path}/%*.png',  # input
        ]

    def _get_ffmpeg_mp4_output_args(self, fps, width, height):
        fps = fps or 60

        # h264 needs both dimensions to be divisible by two.
        # `-2` tells ffmpeg to generate the all missing dimensions, to keep the
        # aspect ratio, and then decrease it until it is divisible by two.
        width = int(width or -2)
        height = int(height or -2)

        if width % 2 != 0 or height % 2 != 0:
            raise ValueError('both width and height have to be divisible by 2')

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
        width = int(width or -1)
        height = int(height or -1)

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
        width = int(width or -1)
        height = int(height or -1)

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
    def write_frame(self, timestamp, image_data):
        if not self.state == 'recording':
            return

        try:
            frame_number = self._frame_counter.increment()

            path = os.path.join(
                self._frame_dir_path,
                f'{frame_number:024d}.png',
            )

            # write image to temp dir
            with open(path, 'wb') as file_handle:
                file_handle.write(image_data)

            # set the file timestamps to the frame timestamps for ffmpeg
            # to pickup
            os.utime(path, (timestamp, timestamp))

        except Exception:
            self._state = 'crashed'

            self.logger.exception('exception raised while writing to ffmpeg')

    def start(self, output_path, width=0, height=0, fps=0, frame_dir=None):
        self._output_path = output_path
        self._output_format = os.path.splitext(output_path)[1][1:]

        self.logger.debug('starting recording to %s', self._output_path)

        if self._output_format not in ('mp4', 'webm', 'gif'):
            raise ValueError(f'invalid output format: {self._output_format}')

        # update internal state
        if self.state != 'idle':
            raise ValueError('recorder is not idling')

        # setup frame dir
        if not frame_dir:
            self._frame_temp_dir = tempfile.TemporaryDirectory()
            self._frame_dir_path = self._frame_temp_dir.name

        else:
            self._frame_temp_dir = None
            self._frame_dir_path = frame_dir

        self.logger.debug('saving frames to %s', self._frame_dir_path)

        # reset frame count
        self._frame_counter.set(0)

        # setup ffmpeg output args
        # mp4
        if self._output_format == 'mp4':
            self._output_args = self._get_ffmpeg_mp4_output_args(
                fps=fps,
                width=width,
                height=height,
            )

        # webm
        elif self._output_format == 'webm':
            self._output_args = self._get_ffmpeg_webm_output_args(
                fps=fps,
                width=width,
                height=height,
            )

        # gif
        elif self._output_format == 'gif':
            self._output_args = self._get_ffmpeg_gif_output_args(
                fps=fps,
                width=width,
                height=height,
            )

        # check if output path is writeable
        self._touch(path=output_path)

        # start accepting frames
        self._state = 'recording'

    def stop(self):
        if self.state != 'recording':
            self.logger.debug('stopping. nothing to do')

            return

        self.logger.debug('stopping recording to %s', self._output_path)

        # render images to video
        logger = self._get_sub_logger('ffmpeg.rendering')

        stdout_lines = []

        command = [
            get_executable('ffmpeg'),
            *self._get_ffmpeg_global_args(),
            *self._get_ffmpeg_input_args(),
            *self._output_args,
            self._output_path,
        ]

        self.logger.debug(
            'rendering %s frames from %s to %s',
            self._frame_counter.value,
            self._frame_dir_path,
            self._output_path,
        )

        self._state = 'rendering'

        exit_code = Process(
            command=command,
            on_stdout_line=lambda line: stdout_lines.append(line),
            logger=logger,
        ).wait()

        if exit_code != 0:
            self._state = 'crashed'

            logger.error(
                'ffmpeg returned %s\n'
                'command: %s \n'
                'stdout/stderr:\n%s',
                exit_code,
                command,
                '\n'.join(stdout_lines),
            )

            raise RuntimeError(f'ffmpeg returned {exit_code}')

        # cleanup
        if self._frame_temp_dir:
            self._frame_temp_dir.cleanup()

        self._state = 'idle'
